function forearm_gripper_ik_v3
% FOREARM_GRIPPER_IK_V3
% 前臂-腕部-平行夹爪解析逆运动学验证脚本。
%
% 目标：在 V2 运动学模型已基本打通后，先用独立脚本验证解析逆解：
%   1) FK(q_true) 生成目标位姿
%   2) IK(T_target) 求候选解
%   3) FK(q_ik) 回代检查位置/姿态误差
%
% 说明：
%   - q = [q1;q2;q3;g]，内部 rad，显示 deg
%   - TCP 是两侧指尖轴沿局部 +X 前移 40 mm 后的中点
%   - g 按 PDF 理论限位 0~90 deg
%   - 该 4 自由度模型不能任意实现 6D 位姿；本脚本主要验证“由自身 FK 产生的目标”能被 IK 找回。

clear; clc; close all;
model = createModel();

fprintf('\n========== Forearm Gripper IK V3 ==========' );
fprintf('\n模型：q=[q1 q2 q3 g]，单位显示 deg，内部 rad\n');
fprintf('TCP：两指尖接触参考点中点，contactX = %.1f mm\n', model.grip.contactX);
fprintf('夹爪耦合：[qA qB qTipA qTipB]^T = [1 -1 -1 1]^T g\n');

%% 1. 单组示例
qTrueDeg = [35; -42; 70; 28];
qTrue = deg2rad(qTrueDeg);
[Ttarget,~] = fkineModel(qTrue, model);

opts.qCurrent = deg2rad([0; -20; 0; 20]);
opts.positionOnly = false;
opts.verbose = true;
sol = ikineAnalytic(Ttarget, model, opts);

fprintf('\n========== 单组 FK -> IK 闭环测试 ==========' );
fprintf('\n真实 q_true [deg] = [%8.3f %8.3f %8.3f %8.3f]\n', qTrueDeg);
printSolutionTable(sol, qTrue, model);

%% 2. 随机批量测试
rng(7);
N = 80;
pass = 0; fail = 0; maxPosErr = 0; maxRotErr = 0;
for k = 1:N
    q = randomSafeQ(model);
    [T,~] = fkineModel(q, model);
    opts.qCurrent = q + deg2rad([3;-3;5;2]).*randn(4,1);
    opts.positionOnly = false;
    opts.verbose = false;
    s = ikineAnalytic(T, model, opts);
    if isempty(s.q)
        fail = fail + 1;
        continue;
    end
    best = s.q(:,1);
    [Tb,~] = fkineModel(best, model);
    pe = norm(Tb(1:3,4)-T(1:3,4));
    re = rotationError(Tb(1:3,1:3), T(1:3,1:3));
    maxPosErr = max(maxPosErr, pe);
    maxRotErr = max(maxRotErr, re);
    if pe < 1e-7 && re < 1e-8
        pass = pass + 1;
    else
        fail = fail + 1;
    end
end
fprintf('\n========== 随机闭环测试 ==========' );
fprintf('\n测试数量：%d\n通过：%d\n失败：%d\n最大位置误差：%.3e mm\n最大姿态误差：%.3e rad\n', ...
    N, pass, fail, maxPosErr, maxRotErr);

%% 3. 不可达目标示例
Tbad = eye(4);
Tbad(1:3,4) = [500; 0; 0];
opts.qCurrent = zeros(4,1);
opts.positionOnly = false;
opts.verbose = true;
sBad = ikineAnalytic(Tbad, model, opts);
fprintf('\n========== 不可达目标测试 ==========' );
if isempty(sBad.q)
    fprintf('\n正确：目标 [500,0,0] mm 超出机构可达半径，未返回解。\n');
else
    fprintf('\n警告：不可达目标却返回了解，需要检查可达性逻辑。\n');
end

fprintf('\n\n运行完成。下一步可以把该 IK 函数集成进 V2 控制面板，增加目标输入和“求解/移动”按钮。\n');

end

%% ======================== 解析逆解 ========================
function sol = ikineAnalytic(Td, model, opts)
if nargin < 3 || isempty(opts), opts = struct; end
if ~isfield(opts,'qCurrent'), opts.qCurrent = zeros(4,1); end
if ~isfield(opts,'positionOnly'), opts.positionOnly = false; end
if ~isfield(opts,'verbose'), opts.verbose = false; end

p = Td(1:3,4);
Rd = Td(1:3,1:3);
qCurrent = opts.qCurrent;

% TCP 相对 Wrist Pitch 轴的距离 L 由位置半径直接给出。
d = p - [model.L12;0;0];
L = norm(d);

% L(g)=L23+rootX+linkX*cos(g)-linkY*sin(g)+contactX
base = model.L23 + model.grip.rootX + model.grip.contactX;
gList = solveGFromL(L, base, model.grip.linkX, -model.grip.linkY, model.qlim(4,:));

if opts.verbose
    fprintf('\n目标点 p=[%.4f %.4f %.4f] mm，相对 Pitch 半径 L=%.6f mm\n', p, L);
    fprintf('候选 g 数量：%d\n', numel(gList));
end

Q = []; info = [];
if isempty(gList)
    sol = emptySol('目标位置半径不在夹爪 g 的可达半径范围内');
    if opts.verbose, fprintf('IK 失败：%s\n', sol.reason); end
    return;
end

for ig = 1:numel(gList)
    g = gList(ig);
    c2 = (p(1)-model.L12)/L;
    c2 = min(1,max(-1,c2));
    q2cands = uniqueTol([acos(c2), -acos(c2)], 1e-10);

    for iq2 = 1:numel(q2cands)
        q2 = wrapToPiLocal(q2cands(iq2));
        if ~inLimit(q2, model.qlim(2,:)), continue; end
        s2 = sin(q2);

        if abs(s2) < 1e-9
            % 位置落在 X 轴附近，q1 由位置不可确定。先取当前 q1。
            q1cands = qCurrent(1);
        else
            sinq1 = p(2)/(L*s2);
            cosq1 = -p(3)/(L*s2);
            q1cands = atan2(sinq1, cosq1);
        end

        for iq1 = 1:numel(q1cands)
            q1 = normalizeToLimit(q1cands(iq1), model.qlim(1,:));
            if isnan(q1), continue; end

            if opts.positionOnly
                q3 = normalizeToLimit(qCurrent(3), model.qlim(3,:));
                if isnan(q3), q3 = 0; end
            else
                Rpre = Rx3(q1)*Ry3(q2);
                Rrel = Rpre.' * Rd;
                q3raw = atan2(Rrel(3,2), Rrel(2,2));
                q3 = normalizeToLimit(q3raw, model.qlim(3,:));
                if isnan(q3), continue; end
            end

            q = [q1;q2;q3;g];
            if any(q < model.qlim(:,1)-1e-10 | q > model.qlim(:,2)+1e-10), continue; end
            [Tc,~] = fkineModel(q, model);
            posErr = norm(Tc(1:3,4)-p);
            rotErr = rotationError(Tc(1:3,1:3), Rd);
            if opts.positionOnly
                ok = posErr < 1e-6;
            else
                ok = posErr < 1e-6 && rotErr < 1e-8;
            end
            if ok
                Q(:,end+1) = q; %#ok<AGROW>
                info(:,end+1) = [posErr; rotErr; jointDistance(q,qCurrent)]; %#ok<AGROW>
            end
        end
    end
end

if isempty(Q)
    sol = emptySol('候选角经过限位和位姿兼容性检查后为空');
    if opts.verbose, fprintf('IK 失败：%s\n', sol.reason); end
    return;
end

% 去重并按离当前关节角最近排序
[Q, info] = uniqueSolutions(Q, info);
[~,idx] = sort(info(3,:));
Q = Q(:,idx); info = info(:,idx);
sol.q = Q;
sol.info = info;
sol.reason = '';
if opts.verbose
    fprintf('IK 成功：得到 %d 组候选解，已按离当前姿态最近排序。\n', size(Q,2));
end
end

function s = emptySol(reason)
s.q = zeros(4,0);
s.info = zeros(3,0);
s.reason = reason;
end

function gList = solveGFromL(L, base, A, B, qlim)
% 解 base + A*cos(g) + B*sin(g) = L, g in qlim。
R = hypot(A,B);
alpha = atan2(B,A);
y = (L-base)/R;
if y < -1-1e-10 || y > 1+1e-10
    gList = [];
    return;
end
y = min(1,max(-1,y));
raw = [alpha + acos(y), alpha - acos(y)];
raw = [raw, raw+2*pi, raw-2*pi];
gList = [];
for k=1:numel(raw)
    g = raw(k);
    if inLimit(g, qlim)
        if abs(base + A*cos(g) + B*sin(g) - L) < 1e-7
            gList(end+1) = g; %#ok<AGROW>
        end
    end
end
gList = uniqueTol(gList,1e-10);
end

%% ======================== 正运动学 ========================
function [Ttcp,K] = fkineModel(q,m)
q1=q(1); q2=q(2); q3=q(3); g=q(4);
T01=Rx(q1);
T_pitch=T01*Tx(m.L12);
T02=T_pitch*Ry(q2);
T_roll=T02*Tx(m.L23);
T03=T_roll*Rx(q3);
qGrip=m.grip.coupling*g;
TA=T03*Tr(m.grip.rootX,m.grip.rootY,0)*Rz(qGrip(1));
TB=T03*Tr(m.grip.rootX,-m.grip.rootY,0)*Rz(qGrip(2));
TTA=TA*Tr(m.grip.linkX,m.grip.linkY,0)*Rz(qGrip(3));
TTB=TB*Tr(m.grip.linkX,-m.grip.linkY,0)*Rz(qGrip(4));
pCA=TTA(1:3,4)+TTA(1:3,1:3)*[m.grip.contactX;0;0];
pCB=TTB(1:3,4)+TTB(1:3,1:3)*[m.grip.contactX;0;0];
pTCP=0.5*(pCA+pCB);
Ttcp=[T03(1:3,1:3),pTCP;0 0 0 1];
K.T03=T03; K.pCA=pCA; K.pCB=pCB; K.qGrip=qGrip;
end

function model = createModel()
model.L12 = 50;
model.L23 = 30;
model.grip.rootX = 54;
model.grip.rootY = 6;
model.grip.linkX = 53;
model.grip.linkY = 2;
model.grip.contactX = 40;
model.grip.coupling = [1;-1;-1;1];
model.qlim = deg2rad([-180 180; -90 15; -180 180; 0 90]);
end

%% ======================== 工具函数 ========================
function q = randomSafeQ(m)
lo=m.qlim(:,1); hi=m.qlim(:,2);
q = lo + (hi-lo).*rand(4,1);
% 避开 q2=0 附近，降低欧拉分解奇异对批量统计的干扰
while abs(rad2deg(q(2))) < 2
    q(2) = lo(2) + (hi(2)-lo(2))*rand;
end
end

function printSolutionTable(sol, qTrue, model)
if isempty(sol.q)
    fprintf('未找到解：%s\n', sol.reason);
    return;
end
fprintf('候选解数量：%d\n', size(sol.q,2));
fprintf('序号 |      q1       q2       q3        g  | posErr(mm) rotErr(rad) distToCurrent\n');
for i=1:size(sol.q,2)
    qd=rad2deg(sol.q(:,i));
    fprintf('%4d | %8.3f %8.3f %8.3f %8.3f | %.3e  %.3e  %.3e\n', ...
        i, qd(1), qd(2), qd(3), qd(4), sol.info(1,i), sol.info(2,i), sol.info(3,i));
end
fprintf('真实角与第1候选角的逐关节 wrap 差 [deg]：\n');
d=rad2deg(wrapToPiLocal(sol.q(:,1)-qTrue));
d(4)=rad2deg(sol.q(4,1)-qTrue(4));
disp(d.');
% 限位再次显示
fprintf('限位 [deg]：\n');
disp(rad2deg(model.qlim));
end

function d = jointDistance(q,q0)
dq = wrapToPiLocal(q-q0);
dq(4) = q(4)-q0(4);
d = norm(dq);
end

function [Q2,I2] = uniqueSolutions(Q,I)
keep = true(1,size(Q,2));
for i=1:size(Q,2)
    if ~keep(i), continue; end
    for j=i+1:size(Q,2)
        if norm(wrapToPiLocal(Q(:,i)-Q(:,j))) < 1e-8
            keep(j)=false;
        end
    end
end
Q2=Q(:,keep); I2=I(:,keep);
end

function a = uniqueTol(a,tol)
if isempty(a), return; end
a = sort(a(:).');
keep = [true, abs(diff(a))>tol];
a = a(keep);
end

function tf = inLimit(q, lim)
tf = q >= lim(1)-1e-10 && q <= lim(2)+1e-10;
end

function q = normalizeToLimit(qraw, lim)
cands = qraw + 2*pi*(-2:2);
valid = cands(cands >= lim(1)-1e-10 & cands <= lim(2)+1e-10);
if isempty(valid)
    q = NaN;
else
    [~,idx] = min(abs(valid-qraw));
    q = valid(idx);
end
end

function e = rotationError(Ra,Rb)
R = Ra.'*Rb;
c = (trace(R)-1)/2;
c = min(1,max(-1,c));
e = acos(c);
end

function x = wrapToPiLocal(x)
x = mod(x+pi,2*pi)-pi;
end

function R=Rx3(q), c=cos(q);s=sin(q);R=[1 0 0;0 c -s;0 s c];end
function R=Ry3(q), c=cos(q);s=sin(q);R=[c 0 s;0 1 0;-s 0 c];end
function T=Rx(q), T=eye(4);T(1:3,1:3)=Rx3(q);end
function T=Ry(q), T=eye(4);T(1:3,1:3)=Ry3(q);end
function T=Rz(q), c=cos(q);s=sin(q);T=[c -s 0 0;s c 0 0;0 0 1 0;0 0 0 1];end
function T=Tx(x), T=eye(4);T(1,4)=x;end
function T=Tr(x,y,z), T=eye(4);T(1:3,4)=[x;y;z];end
