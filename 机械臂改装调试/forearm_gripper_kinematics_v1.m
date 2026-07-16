%% forearm_gripper_kinematics_v1.m
% 前臂-手腕-平行四边形夹爪：第一版运动学、雅可比与STL零位验证
% MATLAB R2024b + Peter Corke Robotics Toolbox 10.4
%
% 独立广义坐标 q = [q1; q2; q3; g]，单位均为 rad：
%   q1: 前臂绕 X 轴旋转
%   q2: 手腕绕局部 Y 轴俯仰
%   q3: 手腕绕局部 X 轴滚转
%   g : 夹爪单自由度开合变量
%
% 夹爪约束：
%   qFingerA = -g, qFingerB = +g
%   qTipA    = +g, qTipB    = -g
%
% 所有长度单位：mm；雅可比线速度部分单位：mm/rad。

clear; clc; close all;

%% 1. 路径和显示设置
stlDir = 'D:\假肢机械臂\机械臂改装调试\原始资料\STL模型\stl_files';
assert(isfolder(stlDir), '找不到 STL 文件夹：%s', stlDir);

showSTL      = true;       % false 时只画运动学骨架和坐标轴
maxMeshFaces = 25000;      % 降低高面数 socket 的显示负担；不改变原 STL
frameScale   = 25;         % 坐标系箭头长度，mm

%% 2. 根据 PDF 建立模型参数
model.L12 = 50;            % 前臂轴 -> Wrist Pitch 轴
model.L23 = 30;            % Wrist Pitch 轴 -> Wrist Roll 轴

% 在 Wrist Roll/Gripper 坐标系中的夹爪尺寸
model.grip.rootX  = 54;    % 80 -> 134
model.grip.rootY  = 6;
model.grip.linkX  = 53;    % 134 -> 187
model.grip.linkY  = 2;

% 指尖关节中点之后的抓取中心轴向偏移，暂未知，先设为 0。
% 以后从 SolidWorks 测得指腹接触面中心后再修改。
model.grip.tcpTipOffsetX = 0;

% 关节限位，单位 rad
model.qlim = deg2rad([ ...
    -180, 180; ...         % q1
     -90,  15; ...         % q2
    -180, 180; ...         % q3
       0,  90]);           % g

%% 3. 选择一组测试关节角
qDeg = [30; -40; 20; 25];
q = deg2rad(qDeg);
checkJointLimits(q, model.qlim);

%% 4. 正运动学
[Ttcp, frames] = fkineForearmGripper(q, model);

fprintf('\n========== 当前测试姿态 ==========\n');
fprintf('q1 = %8.3f deg\n', qDeg(1));
fprintf('q2 = %8.3f deg\n', qDeg(2));
fprintf('q3 = %8.3f deg\n', qDeg(3));
fprintf('g  = %8.3f deg\n', qDeg(4));
fprintf('\n抓取参考点位置 [mm]：\n');
disp(Ttcp(1:3,4).');
fprintf('抓取参考坐标系旋转矩阵：\n');
disp(Ttcp(1:3,1:3));

%% 5. 解析几何雅可比（空间/基坐标系表达）
J = jacobianForearmGripper(q, model);

fprintf('解析几何雅可比 J0，尺寸 %d x %d：\n', size(J,1), size(J,2));
fprintf('前 3 行为线速度 [mm/s]，后 3 行为角速度 [rad/s]\n');
disp(J);

fprintf('各列含义：[q1, q2, q3, g]\n');
fprintf('注意：当前 TCP 在腕滚转轴线上，所以 q3 的线速度列理论上接近 0。\n');
fprintf('平行四边形使夹爪开合不改变 TCP 坐标系姿态，所以 g 的角速度列为 0。\n');

%% 6. 用有限差分检查解析雅可比
[Jnum, errorInfo] = numericalJacobian(@(qq) fkineOnly(qq, model), q);

fprintf('\n========== 雅可比有限差分验证 ==========\n');
fprintf('||J_analytic - J_numeric||_F = %.6e\n', errorInfo.frobenius);
fprintf('最大元素绝对误差             = %.6e\n', errorInfo.maxAbs);
fprintf('数值雅可比：\n');
disp(Jnum);

if errorInfo.maxAbs < 1e-5
    fprintf('验证通过：解析雅可比与数值雅可比一致。\n');
else
    warning('雅可比误差偏大，需要检查模型、差分步长或坐标系定义。');
end

%% 7. 输出关键关节点位置
fprintf('\n========== 关键点世界坐标 [mm] ==========\n');
printPoint('前臂旋转轴原点', frames.p1);
printPoint('Wrist Pitch 轴', frames.p2);
printPoint('Wrist Roll 轴', frames.p3);
printPoint('Finger A 根部', frames.pFingerA);
printPoint('Finger B 根部', frames.pFingerB);
printPoint('Fingertip A 轴', frames.pTipA);
printPoint('Fingertip B 轴', frames.pTipB);
printPoint('抓取参考点', Ttcp(1:3,4));

%% 8. 绘制 STL、运动学骨架和关节轴
figure('Color','w', 'Name','Forearm Gripper Kinematics V1');
ax = axes; hold(ax,'on'); grid(ax,'on'); axis(ax,'equal');
xlabel(ax,'X / mm'); ylabel(ax,'Y / mm'); zlabel(ax,'Z / mm');
title(ax, sprintf('q = [%.1f, %.1f, %.1f, %.1f] deg', qDeg), 'Interpreter','none');
view(ax, 35, 25);

if showSTL
    files.socket      = 'socket.stl';
    files.wristBody   = 'wrsit_body.stl';
    files.wristRoll   = 'wrist_roll.stl';
    files.gripperBody = 'gripper_body.stl';
    files.fingerA     = 'finger_body_a.stl';
    files.fingerB     = 'finger_body_b.stl';
    files.tipA        = 'fingertip_a.stl';
    files.tipB        = 'fingertip_b.stl';

    colors.socket      = [0.35 0.35 0.38];
    colors.wristBody   = [0.20 0.48 0.80];
    colors.wristRoll   = [0.25 0.68 0.72];
    colors.gripperBody = [0.85 0.55 0.18];
    colors.fingerA     = [0.82 0.25 0.22];
    colors.fingerB     = [0.82 0.25 0.22];
    colors.tipA        = [0.95 0.72 0.25];
    colors.tipB        = [0.95 0.72 0.25];

    drawSTL(ax, fullfile(stlDir,files.socket),      eye(4),             colors.socket,      maxMeshFaces);
    drawSTL(ax, fullfile(stlDir,files.wristBody),   frames.T_wristBody, colors.wristBody,   maxMeshFaces);
    drawSTL(ax, fullfile(stlDir,files.wristRoll),   frames.T_wristRoll, colors.wristRoll,   maxMeshFaces);
    drawSTL(ax, fullfile(stlDir,files.gripperBody), frames.T_gripper,   colors.gripperBody, maxMeshFaces);
    drawSTL(ax, fullfile(stlDir,files.fingerA),     frames.T_fingerA,   colors.fingerA,     maxMeshFaces);
    drawSTL(ax, fullfile(stlDir,files.fingerB),     frames.T_fingerB,   colors.fingerB,     maxMeshFaces);
    drawSTL(ax, fullfile(stlDir,files.tipA),        frames.T_tipA,      colors.tipA,        maxMeshFaces);
    drawSTL(ax, fullfile(stlDir,files.tipB),        frames.T_tipB,      colors.tipB,        maxMeshFaces);
end

% 画运动学骨架
plot3(ax, [frames.p1(1),frames.p2(1),frames.p3(1)], ...
          [frames.p1(2),frames.p2(2),frames.p3(2)], ...
          [frames.p1(3),frames.p2(3),frames.p3(3)], ...
          'k.-','LineWidth',2,'MarkerSize',18);
plot3(ax, [frames.p3(1),frames.pFingerA(1),frames.pTipA(1)], ...
          [frames.p3(2),frames.pFingerA(2),frames.pTipA(2)], ...
          [frames.p3(3),frames.pFingerA(3),frames.pTipA(3)], ...
          'm.-','LineWidth',2,'MarkerSize',16);
plot3(ax, [frames.p3(1),frames.pFingerB(1),frames.pTipB(1)], ...
          [frames.p3(2),frames.pFingerB(2),frames.pTipB(2)], ...
          [frames.p3(3),frames.pFingerB(3),frames.pTipB(3)], ...
          'm.-','LineWidth',2,'MarkerSize',16);

% 世界坐标系与各主要坐标系
drawFrame(ax, eye(4),             frameScale, '{0}');
drawFrame(ax, frames.T_pitch,     frameScale, '{2} Pitch');
drawFrame(ax, frames.T_gripper,   frameScale, '{G} Roll');
drawFrame(ax, Ttcp,               frameScale, '{TCP}');

% 关节旋转轴：红 q1，绿 q2，红 q3，蓝色夹爪各 Z 轴
drawJointAxis(ax, frames.p1, frames.a1, 90, [0.8 0.1 0.1], 'q_1');
drawJointAxis(ax, frames.p2, frames.a2, 90, [0.1 0.65 0.1], 'q_2');
drawJointAxis(ax, frames.p3, frames.a3, 90, [0.8 0.1 0.1], 'q_3');
drawJointAxis(ax, frames.pFingerA, frames.aGripZ, 55, [0.1 0.25 0.9], 'A');
drawJointAxis(ax, frames.pFingerB, frames.aGripZ, 55, [0.1 0.25 0.9], 'B');
drawJointAxis(ax, frames.pTipA, frames.aFingerAZ, 45, [0.15 0.45 1.0], 'Tip A');
drawJointAxis(ax, frames.pTipB, frames.aFingerBZ, 45, [0.15 0.45 1.0], 'Tip B');

% 抓取参考点
plot3(ax,Ttcp(1,4),Ttcp(2,4),Ttcp(3,4),'kp','MarkerFaceColor','y','MarkerSize',13);

camlight(ax,'headlight'); lighting(ax,'gouraud');
axis(ax,'vis3d');

fprintf('\n程序运行完成。请重点观察：\n');
fprintf('1) STL 是否在所有关节处正确连接；\n');
fprintf('2) 彩色关节轴是否穿过实际销轴中心；\n');
fprintf('3) A/B 指腹是否保持平行；\n');
fprintf('4) 命令行中的雅可比有限差分误差是否足够小。\n');

%% ====================== 局部函数 ======================

function [Ttcp, F] = fkineForearmGripper(q, model)
%FKINEFOREARMGRIPPER 计算完整主动坐标运动学。
% q = [q1;q2;q3;g]，rad。

    q1 = q(1); q2 = q(2); q3 = q(3); g = q(4);

    % 主腕部：X-Y-X
    T01 = Rx(q1);
    T_pitch = T01 * Tx(model.L12);
    T02 = T_pitch * Ry(q2);
    T_roll = T02 * Tx(model.L23);
    T03 = T_roll * Rx(q3);       % Gripper/Wrist Roll 坐标系

    % 夹爪四个实际转动副受一个主动变量 g 约束
    qA    = -g;
    qB    =  g;
    qTipA =  g;
    qTipB = -g;

    T_fingerA = T03 * Tr(model.grip.rootX, model.grip.rootY,0) * Rz(qA);
    T_fingerB = T03 * Tr(model.grip.rootX,-model.grip.rootY,0) * Rz(qB);

    T_tipA = T_fingerA * Tr(model.grip.linkX, model.grip.linkY,0) * Rz(qTipA);
    T_tipB = T_fingerB * Tr(model.grip.linkX,-model.grip.linkY,0) * Rz(qTipB);

    % 两个指尖关节的中点，外加未来可标定的指腹轴向偏移。
    pMid = 0.5*(T_tipA(1:3,4) + T_tipB(1:3,4));
    pTcp = pMid + T03(1:3,1:3)*[model.grip.tcpTipOffsetX;0;0];

    % 平行四边形约束使指腹/TCP 姿态相对 Gripper 保持不变。
    Ttcp = [T03(1:3,1:3), pTcp; 0 0 0 1];

    % 保存绘图、雅可比和调试需要的中间结果
    F.T01 = T01;
    F.T_pitch = T_pitch;
    F.T02 = T02;
    F.T_roll = T_roll;
    F.T03 = T03;
    F.T_gripper = T03;
    F.T_wristBody = T01;
    F.T_wristRoll = T02;         % STL 原点假定在 Wrist Pitch 轴
    F.T_fingerA = T_fingerA;
    F.T_fingerB = T_fingerB;
    F.T_tipA = T_tipA;
    F.T_tipB = T_tipB;

    F.p1 = [0;0;0];
    F.p2 = T_pitch(1:3,4);
    F.p3 = T_roll(1:3,4);
    F.pFingerA = T_fingerA(1:3,4);
    F.pFingerB = T_fingerB(1:3,4);
    F.pTipA = T_tipA(1:3,4);
    F.pTipB = T_tipB(1:3,4);

    F.a1 = [1;0;0];
    F.a2 = T01(1:3,1:3)*[0;1;0];
    F.a3 = T02(1:3,1:3)*[1;0;0];
    F.aGripZ = T03(1:3,1:3)*[0;0;1];
    F.aFingerAZ = T_fingerA(1:3,1:3)*[0;0;1];
    F.aFingerBZ = T_fingerB(1:3,1:3)*[0;0;1];
end

function T = fkineOnly(q, model)
    T = fkineForearmGripper(q, model);
end

function J = jacobianForearmGripper(q, model)
%JACOBIANFOREARMGRIPPER 基坐标系表达的 6x4 几何雅可比。
% 上三行：TCP 线速度；下三行：TCP 角速度。

    [Ttcp,F] = fkineForearmGripper(q, model);
    p = Ttcp(1:3,4);

    Jv1 = cross(F.a1, p-F.p1);
    Jv2 = cross(F.a2, p-F.p2);
    Jv3 = cross(F.a3, p-F.p3);

    % 夹爪中点在 Gripper 坐标系 X 方向的位置：
    % x(g) = rootX + linkX*cos(g) + linkY*sin(g) + tcpTipOffsetX
    % dx/dg = -linkX*sin(g) + linkY*cos(g)
    g = q(4);
    dx_dg = -model.grip.linkX*sin(g) + model.grip.linkY*cos(g);
    Jv4 = F.T03(1:3,1:3)*[dx_dg;0;0];

    Jw1 = F.a1;
    Jw2 = F.a2;
    Jw3 = F.a3;
    Jw4 = [0;0;0];

    J = [Jv1,Jv2,Jv3,Jv4;
         Jw1,Jw2,Jw3,Jw4];
end

function [Jnum, info] = numericalJacobian(fkFun, q)
%NUMERICALJACOBIAN 用中心差分验证 6xN 空间几何雅可比。

    h = 1e-7;
    n = numel(q);
    Jnum = zeros(6,n);
    T0 = fkFun(q);
    R0 = T0(1:3,1:3);

    for i = 1:n
        dq = zeros(n,1); dq(i)=h;
        Tp = fkFun(q+dq);
        Tm = fkFun(q-dq);

        Jnum(1:3,i) = (Tp(1:3,4)-Tm(1:3,4))/(2*h);

        % Rdot*R' 是基坐标系表达的空间角速度反对称矩阵
        Rdot = (Tp(1:3,1:3)-Tm(1:3,1:3))/(2*h);
        Omega = Rdot*R0.';
        Omega = 0.5*(Omega-Omega.');
        Jnum(4:6,i) = [Omega(3,2); Omega(1,3); Omega(2,1)];
    end

    Janalytic = jacobianForearmGripper(q, evalinModel(fkFun));
    D = Janalytic-Jnum;
    info.frobenius = norm(D,'fro');
    info.maxAbs = max(abs(D),[],'all');
end

function model = evalinModel(fkFun)
%EVALINMODEL 从匿名函数工作区提取 model，仅用于本验证脚本。
    s = functions(fkFun);
    model = s.workspace{1}.model;
end

function drawSTL(ax, fileName, T, color, maxFaces)
    assert(isfile(fileName), '缺少 STL 文件：%s', fileName);
    TR = stlread(fileName);
    F = TR.ConnectivityList;
    V = TR.Points;

    if size(F,1) > maxFaces
        [F,V] = reducepatch(F,V,maxFaces);
    end

    Vw = transformVertices(V,T);
    patch(ax,'Faces',F,'Vertices',Vw, ...
        'FaceColor',color,'EdgeColor','none', ...
        'FaceAlpha',1.0,'AmbientStrength',0.35, ...
        'DiffuseStrength',0.75,'SpecularStrength',0.12);
end

function Vw = transformVertices(V,T)
    Vh = [V,ones(size(V,1),1)];
    temp = (T*Vh.').';
    Vw = temp(:,1:3);
end

function drawFrame(ax,T,s,nameText)
    p=T(1:3,4); R=T(1:3,1:3);
    quiver3(ax,p(1),p(2),p(3),s*R(1,1),s*R(2,1),s*R(3,1),0,'r','LineWidth',1.7);
    quiver3(ax,p(1),p(2),p(3),s*R(1,2),s*R(2,2),s*R(3,2),0,'g','LineWidth',1.7);
    quiver3(ax,p(1),p(2),p(3),s*R(1,3),s*R(2,3),s*R(3,3),0,'b','LineWidth',1.7);
    text(ax,p(1),p(2),p(3),['  ',nameText],'FontWeight','bold','Color','k');
end

function drawJointAxis(ax,p,a,totalLength,color,nameText)
    a=a/norm(a);
    p0=p-0.5*totalLength*a;
    p1=p+0.5*totalLength*a;
    plot3(ax,[p0(1),p1(1)],[p0(2),p1(2)],[p0(3),p1(3)], ...
        '--','Color',color,'LineWidth',2.0);
    text(ax,p1(1),p1(2),p1(3),[' ',nameText],'Color',color,'FontWeight','bold');
end

function checkJointLimits(q, qlim)
    if numel(q) ~= size(qlim,1)
        error('q 的长度与关节限位数量不一致。');
    end
    bad = find(q < qlim(:,1)-1e-12 | q > qlim(:,2)+1e-12);
    if ~isempty(bad)
        error('关节 %s 超出限位。', mat2str(bad.'));
    end
end

function printPoint(name,p)
    fprintf('%-20s = [%10.4f, %10.4f, %10.4f]\n',name,p(1),p(2),p(3));
end

function T=Rx(q)
    c=cos(q); s=sin(q);
    T=[1 0 0 0; 0 c -s 0; 0 s c 0; 0 0 0 1];
end

function T=Ry(q)
    c=cos(q); s=sin(q);
    T=[c 0 s 0; 0 1 0 0; -s 0 c 0; 0 0 0 1];
end

function T=Rz(q)
    c=cos(q); s=sin(q);
    T=[c -s 0 0; s c 0 0; 0 0 1 0; 0 0 0 1];
end

function T=Tx(x)
    T=eye(4); T(1,4)=x;
end

function T=Tr(x,y,z)
    T=eye(4); T(1:3,4)=[x;y;z];
end
