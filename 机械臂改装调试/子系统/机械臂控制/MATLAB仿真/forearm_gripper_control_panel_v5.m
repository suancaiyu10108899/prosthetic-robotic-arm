function forearm_gripper_control_panel_v5
% FOREARM_GRIPPER_CONTROL_PANEL_V5
% 前臂-腕部-平行夹爪：以拖动为核心的所见即所得交互平台。
%
% 核心变化（vs V4）：
%   - TCP 固定在 Gripper Body 上：g=0 时指尖转轴前移 40 mm，即 [147,0,0] in {G}
%   - TCP 不随 g 变化，位置 IK 大幅简化
%   - 拖动为默认交互：选模式 → 在图中拖红点 → 机器人实时跟随
%   - 按钮数量极少，高 DPI 下更可靠

%% 1. 模型
model.stlDir = 'D:\假肢机械臂\机械臂改装调试\原始资料\STL模型\stl_files';
assert(isfolder(model.stlDir), '找不到 STL 文件夹：%s', model.stlDir);
model.L12 = 50;           % 前臂轴 → Wrist Pitch
model.L23 = 30;           % Wrist Pitch → Wrist Roll
% Gripper Body 内固定 TCP：g=0 时指尖转轴 (187,±8,0) 前移 40 mm
model.tcpOffsetInG = [147; 0; 0];  % 80 → 227，mm
% 夹爪几何
model.grip.rootX = 54; model.grip.rootY = 6;
model.grip.linkX = 53; model.grip.linkY = 2;
model.grip.contactX = 40;   % 指尖转轴 → 接触参考点
model.grip.coupling = [1;-1;-1;1]; % qA=+g, qB=-g, qTipA=-g, qTipB=+g
% 限位
model.qlimDeg = [-180 180; -90 15; -180 180; 0 90];
model.qlim = deg2rad(model.qlimDeg);
model.jointNames = {'q1 前臂','q2 俯仰','q3 滚转','g 夹爪'};
model.maxFaces = 25000;
model.frameScale = 24;

%% 2. 读取 STL
files = {'socket.stl','wrsit_body.stl','wrist_roll.stl','gripper_body.stl',...
         'finger_body_a.stl','finger_body_b.stl','fingertip_a.stl','fingertip_b.stl'};
keys  = {'socket','wrBody','wrRoll','gripper','fA','fB','tA','tB'};
colors= [0.35 0.35 0.38; 0.20 0.48 0.80; 0.25 0.68 0.72; 0.85 0.55 0.18; ...
         0.82 0.25 0.22; 0.82 0.25 0.22; 0.95 0.72 0.25; 0.95 0.72 0.25];
mesh = struct;
for i = 1:numel(files)
    TR = stlread(fullfile(model.stlDir, files{i}));
    F = TR.ConnectivityList; V = TR.Points;
    if size(F,1) > model.maxFaces, [F,V] = reducepatch(F,V,model.maxFaces); end
    mesh.(keys{i}) = struct('F',F,'V',V,'color',colors(i,:));
end

%% 3. 状态
state.qDeg = [0;0;0;0];
state.track = zeros(0,3);
state.ikMode = 1;      % 1=自由, 2=球面约束, 3=近球面
state.ikPlane = 2;     % 1=XY, 2=XZ, 3=YZ
state.target = [227;0;0];
state.lastIK = [];
state.isDragging = false;

%% 4. UI
fig = uifigure('Name','前臂-腕部-夹爪 V5 所见即所得', ...
    'Position',[10 10 1680 980], 'Color',[0.96 0.97 0.98]);
main = uigridlayout(fig,[1 2]);
main.ColumnWidth = {890,'1x'}; main.Padding = [6 6 6 6]; main.ColumnSpacing = 6;

% 左：3D 视图
ax = uiaxes(main); ax.Layout.Column = 1;
hold(ax,'on'); grid(ax,'on'); axis(ax,'equal'); axis(ax,'vis3d');
xlabel(ax,'X mm'); ylabel(ax,'Y mm'); zlabel(ax,'Z mm');
view(ax,35,25); ax.XLim=[-250 300]; ax.YLim=[-280 280]; ax.ZLim=[-280 280];
title(ax,'拖动红点控制 TCP — 机器人实时跟随','FontSize',14);

% 右：控制区
right = uitabgroup(main); right.Layout.Column = 2;
tabJ = uitab(right,'Title','关节');     % 关节滑块
tabIK = uitab(right,'Title','拖动IK');  % 拖动为主
tabD = uitab(right,'Title','数据');     % 雅可比/矩阵/点

%% 4.1 关节页
jg = uigridlayout(tabJ,[7 2]);
jg.RowHeight = {50,50,50,50,48,48,'1x'}; jg.ColumnWidth = {80,'1x'};
jg.Padding = [10 10 10 10]; jg.RowSpacing = 6;
slider = gobjects(4,1); fld = gobjects(4,1);
for i = 1:4
    uilabel(jg,'Text',model.jointNames{i},'FontSize',14,'FontWeight','bold');
    sub = uigridlayout(jg,[1 2]); sub.ColumnWidth = {'1x',70}; sub.Padding = [0 0 0 0];
    slider(i) = uislider(sub,'Limits',model.qlimDeg(i,:),'Value',state.qDeg(i));
    fld(i) = uieditfield(sub,'numeric','Limits',model.qlimDeg(i,:),'Value',state.qDeg(i),'ValueDisplayFormat','%.2f','FontSize',14);
    slider(i).ValueChangingFcn = @(~,e) jointMove(i,e.Value);
    fld(i).ValueChangedFcn = @(~,e) jointFld(i,e.Value);
end
btnRow = uigridlayout(jg,[1 4]); btnRow.Padding = [0 0 0 0];
uibutton(btnRow,'Text','零位','ButtonPushedFcn',@(~,~)setJoints([0;0;0;0]));
uibutton(btnRow,'Text','随机','ButtonPushedFcn',@(~,~)setRandomJoints());
uibutton(btnRow,'Text','清轨迹','ButtonPushedFcn',@(~,~)clearTrack());
uibutton(btnRow,'Text','雅可比','ButtonPushedFcn',@(~,~)checkJacobian());

infoText = uitextarea(jg,'Editable','off','FontName','Consolas','FontSize',13);
infoText.Layout.Column = [1 2];

%% 4.2 拖动IK页
ikg = uigridlayout(tabIK,[8 1]);
ikg.RowHeight = {55,75,55,30,50,30,230,'1x'};
ikg.Padding = [10 10 10 10]; ikg.RowSpacing = 4;

uilabel(ikg,'Text','拖动模式（点击 3D 图中的红点开始拖动）','FontSize',14,'FontWeight','bold');

% 模式按钮行
mb = uigridlayout(ikg,[1 3]); mb.Padding = [0 0 0 0]; mb.ColumnSpacing = 8;
mb.ColumnWidth = {'1x','1x','1x'};
btnMode = gobjects(3,1);
btnMode(1) = uibutton(mb,'Text','自由拖动','ButtonPushedFcn',@(~,~)setMode(1),'FontSize',16,'FontWeight','bold');
btnMode(2) = uibutton(mb,'Text','球面约束','ButtonPushedFcn',@(~,~)setMode(2),'FontSize',16,'FontWeight','bold');
btnMode(3) = uibutton(mb,'Text','近球面','ButtonPushedFcn',@(~,~)setMode(3),'FontSize',16,'FontWeight','bold');

% 平面选择
pb = uigridlayout(ikg,[1 5]); pb.Padding = [0 0 0 0]; pb.ColumnSpacing = 8;
uilabel(pb,'Text','拖动平面','FontSize',13);
ddPlane = uidropdown(pb,'Items',{'XY平面','XZ平面','YZ平面'},'Value','XZ平面','FontSize',13,'ValueChangedFcn',@(~,~)planeChanged());
uibutton(pb,'Text','读当前TCP','ButtonPushedFcn',@(~,~)readTCP(),'FontSize',13);
uibutton(pb,'Text','回TCP零位','ButtonPushedFcn',@(~,~)resetTarget(),'FontSize',13);
uibutton(pb,'Text','候选解','ButtonPushedFcn',@(~,~)toggleTable(),'FontSize',13);

% 目标显示（只读）
tg = uigridlayout(ikg,[1 4]); tg.Padding = [0 0 0 0];
uilabel(tg,'Text','目标','FontSize',13,'FontWeight','bold');
ikTargetLabel = uilabel(tg,'Text','[227,0,0]','FontSize',13,'FontName','Consolas');
uilabel(tg,'Text','投影(若有)','FontSize',13,'FontWeight','bold');
ikUsedLabel = uilabel(tg,'Text','-','FontSize',13,'FontName','Consolas');

% 当前解显示
sg = uigridlayout(ikg,[1 5]); sg.Padding = [0 0 0 0];
uilabel(sg,'Text','解','FontSize',13,'FontWeight','bold');
ikSolLabel = uilabel(sg,'Text','q=[0,0,0,0]','FontSize',13,'FontName','Consolas');
ikDistLabel = uilabel(sg,'Text','','FontSize',13,'FontName','Consolas');
uibutton(sg,'Text','应用','ButtonPushedFcn',@(~,~)applyBestIK(),'FontSize',13);
ikTable = uitable(ikg,'ColumnName',{'#','q1','q2','q3','g','err'}, ...
    'ColumnWidth',{30,65,65,65,65,70},'Visible','off');

ikHelp = uitextarea(ikg,'Editable','off','FontName','Consolas','FontSize',12);
ikHelp.Value = {
    '拖动说明：'
    '  自由拖动 — 无约束跟随鼠标'
    '  球面约束 — TCP 锁定在半径 177mm 球面上 (精确 IK)'
    '  近球面 — 自由拖，自动投影到球面'
    '  点击图中红点 -> 拖动 -> 机器人实时跟随'
    };

%% 4.3 数据页
dataTabs = uitabgroup(tabD);
ds1 = uitab(dataTabs,'Title','雅可比');
ds2 = uitab(dataTabs,'Title','关键点');
jText = uitextarea(ds1,'Editable','off','FontName','Consolas','FontSize',12);
tText = uitextarea(ds2,'Editable','off','FontName','Consolas','FontSize',12);

%% 5. 图元
% STL patches
hT = struct; hP = struct;
for i = 1:numel(keys)
    hT.(keys{i}) = hgtransform(ax);
    M = mesh.(keys{i});
    hP.(keys{i}) = patch(ax,'Faces',M.F,'Vertices',M.V,'Parent',hT.(keys{i}), ...
        'FaceColor',M.color,'EdgeColor','none','AmbientStrength',0.3, ...
        'DiffuseStrength',0.7,'SpecularStrength',0.1,'HitTest','off');
end
% 骨架
hSk1 = plot3(ax,nan,nan,nan,'k.-','LineWidth',2.5,'MarkerSize',16,'HitTest','off','PickableParts','none');
hSk2 = plot3(ax,nan,nan,nan,'m.-','LineWidth',2,'MarkerSize',14,'HitTest','off','PickableParts','none');
hSk3 = plot3(ax,nan,nan,nan,'m.-','LineWidth',2,'MarkerSize',14,'HitTest','off','PickableParts','none');
% TCP + 目标
hTCP = plot3(ax,nan,nan,nan,'bp','MarkerFaceColor','b','MarkerSize',14,'HitTest','off','PickableParts','none');
hTarget = plot3(ax,nan,nan,nan,'ro','LineWidth',3,'MarkerSize',14,'PickableParts','all');
hUsed = plot3(ax,nan,nan,nan,'go','LineWidth',2,'MarkerSize',12);
hContact = plot3(ax,nan,nan,nan,'c.','MarkerSize',10,'HitTest','off','PickableParts','none');
% 轨迹
hTrack = plot3(ax,nan,nan,nan,'Color',[0.55 0 0.75],'LineWidth',1.8,'HitTest','off','PickableParts','none');
% 球面
[xx,yy,zz] = sphere(50);
hSphere = surf(ax,xx*177+50,yy*177,zz*177,'FaceAlpha',0.06,'EdgeColor','none','FaceColor',[0.2 0.5 0.9],'HitTest','off','PickableParts','none');
% 坐标轴
hFr = gobjects(2,3);
for i = 1:2
    hFr(i,1) = quiver3(ax,0,0,0,0,0,0,0,'r','LineWidth',1.5,'HitTest','off','PickableParts','none');
    hFr(i,2) = quiver3(ax,0,0,0,0,0,0,0,'g','LineWidth',1.5,'HitTest','off','PickableParts','none');
    hFr(i,3) = quiver3(ax,0,0,0,0,0,0,0,'b','LineWidth',1.5,'HitTest','off','PickableParts','none');
end
ax.ButtonDownFcn = @(~,~)axesClickDrag();
camlight(ax,'headlight'); lighting(ax,'gouraud');

%% 6. 初始更新
setMode(1);
updateAll(false);
readTCP();

%% ===================== 回调 =====================
    function jointMove(i,val)
        state.qDeg(i) = val; fld(i).Value = val;
        updateAll(true);
    end
    function jointFld(i,val)
        state.qDeg(i) = val; slider(i).Value = val;
        updateAll(true);
    end
    function setJoints(qd)
        state.qDeg = qd(:);
        for k = 1:4, slider(k).Value = state.qDeg(k); fld(k).Value = state.qDeg(k); end
        updateAll(false);
    end
    function setRandomJoints()
        lo = model.qlimDeg(:,1); hi = model.qlimDeg(:,2);
        setJoints(lo + (hi-lo).*rand(4,1));
    end
    function clearTrack()
        state.track = zeros(0,3);
        set(hTrack,'XData',nan,'YData',nan,'ZData',nan);
    end
    function checkJacobian()
        q = deg2rad(state.qDeg);
        [J,~,~] = modelKin(q, model);
        Jn = numJac(@(qq)fkOnly(qq,model), q);
        D = J - Jn;
        uialert(fig, sprintf('Frob=%.3e  Max=%.3e', norm(D,'fro'), max(abs(D),[],'all')), '雅可比验证');
    end

    function setMode(m)
        state.ikMode = m;
        for k = 1:3
            if k == m
                btnMode(k).BackgroundColor = [0.2 0.6 1.0];
                btnMode(k).FontColor = [1 1 1];
            else
                btnMode(k).BackgroundColor = [0.94 0.94 0.94];
                btnMode(k).FontColor = [0 0 0];
            end
        end
        % 更新球面显示
        if m == 2, set(hSphere,'FaceAlpha',0.12,'Visible','on');
        else, set(hSphere,'FaceAlpha',0.04,'Visible','on'); end
    end
    function planeChanged()
        items = {'XY平面','XZ平面','YZ平面'};
        state.ikPlane = find(strcmp(ddPlane.Value, items));
    end
    function readTCP()
        q = deg2rad(state.qDeg);
        [~,K,~] = modelKin(q, model);
        state.target = K.pTCP;
        drawTarget();
    end
    function resetTarget()
        state.target = [227;0;0];
        drawTarget();
        solveAndApply();
    end
    function drawTarget()
        set(hTarget,'XData',state.target(1),'YData',state.target(2),'ZData',state.target(3));
        ikTargetLabel.Text = sprintf('[%.2f, %.2f, %.2f]', state.target);
        set(hUsed,'XData',nan,'YData',nan,'ZData',nan);
        ikUsedLabel.Text = '-';
    end

    function axesClickDrag()
        % 获取鼠标在选定平面上的3D位置
        pMouse = mouseOnPlane();
        if any(~isfinite(pMouse)), return; end
        % 判断鼠标是否靠近目标红圈（< 25 mm 视为"拖红圈"）
        dTarget = norm(pMouse - state.target);
        if dTarget < 25
            % 拖动已有目标
            startDrag();
        else
            % 设置新目标
            pConstr = applyConstraint(pMouse);
            state.target = pConstr;
            drawTarget();
            solveAndApply();
            startDrag();
        end
    end
    function startDrag()
        state.isDragging = true;
        fig.WindowButtonMotionFcn = @(~,~)dragMove();
        fig.WindowButtonUpFcn = @(~,~)stopDrag();
    end
    function dragMove()
        if ~state.isDragging, return; end
        p = mouseOnPlane();
        if any(~isfinite(p)), return; end
        p = applyConstraint(p);
        state.target = p;
        drawTarget();
        solveAndApply();
    end
    function stopDrag()
        state.isDragging = false;
        fig.WindowButtonMotionFcn = '';
        fig.WindowButtonUpFcn = '';
    end

    function p = mouseOnPlane()
        cp = ax.CurrentPoint;
        p0 = cp(1,:)'; p1 = cp(2,:)'; v = p1 - p0;
        ref = state.target;
        switch state.ikPlane
            case 1, idx = 3; fixed = ref(3);  % XY
            case 2, idx = 2; fixed = ref(2);  % XZ
            case 3, idx = 1; fixed = ref(1);  % YZ
            otherwise, idx = 2; fixed = ref(2);
        end
        if abs(v(idx)) < 1e-12, p = [nan;nan;nan]; return; end
        t = (fixed - p0(idx)) / v(idx);
        p = p0 + t*v;
    end

    function p = applyConstraint(p)
        C = [model.L12; 0; 0];  % Wrist Pitch 中心
        d = p - C; L = norm(d);
        if L < 1e-9, return; end
        Lc = 177;  % 固定 TCP 半径
        switch state.ikMode
            case 1  % 自由 — 无约束
            case 2  % 球面 — 严格锁定
                p = C + Lc * d / L;
            case 3  % 近球面 — 超出范围时投影
                if abs(L - Lc) > 1
                    p = C + Lc * d / L;
                    set(hUsed,'XData',p(1),'YData',p(2),'ZData',p(3));
                    ikUsedLabel.Text = sprintf('投影 %.1f mm (目标半径 %.1f)', abs(L-Lc), L);
                else
                    set(hUsed,'XData',nan,'YData',nan,'ZData',nan);
                    ikUsedLabel.Text = '-';
                end
        end
    end

    function solveAndApply()
        p = state.target;
        opts.positionOnly = true;
        opts.verbose = false;
        opts.qCurrent = deg2rad(state.qDeg);
        sol = ikFixedTCP(p, model, opts);
        state.lastIK = sol;
        if isempty(sol.q)
            ikSolLabel.Text = '不可达';
            ikDistLabel.Text = '';
            if ~isempty(sol.message)
                ikUsedLabel.Text = sol.message;
            end
            ikTable.Data = {};
            return;
        end
        best = sol.q(:,1);
        ikSolLabel.Text = sprintf('q=[%.1f,%.1f,%.1f,%.1f]', rad2deg(best));
        % 显示离当前姿态距离
        dq = best - deg2rad(state.qDeg);
        dq(1:3) = wrapToPi(dq(1:3));
        ikDistLabel.Text = sprintf('dq=%.1f', norm(dq));
        % 候选表
        nSol = size(sol.q,2);
        tbl = cell(nSol, 6);
        for k = 1:nSol
            qk = rad2deg(sol.q(:,k));
            tbl{k,1} = k;
            for j = 1:4, tbl{k,j+1} = qk(j); end
            tbl{k,6} = sol.errors(k);
        end
        ikTable.Data = tbl;
        % 自动应用推荐解
        state.qDeg = rad2deg(best(:));
        for k = 1:4, slider(k).Value = state.qDeg(k); fld(k).Value = state.qDeg(k); end
        updateAll(false);
    end

    function applyBestIK()
        if isempty(state.lastIK) || isempty(state.lastIK.q)
            uialert(fig,'没有可应用的解','提示'); return;
        end
        setJoints(rad2deg(state.lastIK.q(:,1)));
    end
    function toggleTable()
        if strcmp(ikTable.Visible,'on')
            ikTable.Visible = 'off';
        else
            ikTable.Visible = 'on';
        end
    end

    function updateAll(recordTrack)
        q = deg2rad(state.qDeg);
        [J,K,Ttcp] = modelKin(q, model);
        % STL
        hT.socket.Matrix = eye(4);
        hT.wrBody.Matrix = K.T_wrBody;
        hT.wrRoll.Matrix = K.T_wrRoll;
        hT.gripper.Matrix = K.T_gripper;
        hT.fA.Matrix = K.T_fA;
        hT.fB.Matrix = K.T_fB;
        hT.tA.Matrix = K.T_tA;
        hT.tB.Matrix = K.T_tB;
        % 骨架
        set(hSk1,'XData',[K.p1(1),K.p2(1),K.p3(1),K.pTCP(1)], ...
                 'YData',[K.p1(2),K.p2(2),K.p3(2),K.pTCP(2)], ...
                 'ZData',[K.p1(3),K.p2(3),K.p3(3),K.pTCP(3)]);
        set(hSk2,'XData',[K.p3(1),K.pFA(1),K.pTA(1),K.pCA(1)], ...
                 'YData',[K.p3(2),K.pFA(2),K.pTA(2),K.pCA(2)], ...
                 'ZData',[K.p3(3),K.pFA(3),K.pTA(3),K.pCA(3)]);
        set(hSk3,'XData',[K.p3(1),K.pFB(1),K.pTB(1),K.pCB(1)], ...
                 'YData',[K.p3(2),K.pFB(2),K.pTB(2),K.pCB(2)], ...
                 'ZData',[K.p3(3),K.pFB(3),K.pTB(3),K.pCB(3)]);
        % TCP / 接触点
        pt = K.pTCP;
        set(hTCP,'XData',pt(1),'YData',pt(2),'ZData',pt(3));
        set(hContact,'XData',[K.pCA(1),K.pCB(1)],'YData',[K.pCA(2),K.pCB(2)],'ZData',[K.pCA(3),K.pCB(3)]);
        % 轨迹
        if recordTrack
            state.track(end+1,:) = pt';
            if size(state.track,1) > 3000, state.track = state.track(end-2999:end,:); end
        end
        if isempty(state.track)
            set(hTrack,'XData',nan,'YData',nan,'ZData',nan);
        else
            set(hTrack,'XData',state.track(:,1),'YData',state.track(:,2),'ZData',state.track(:,3));
        end
        % 坐标系
        drawFrame(hFr(1,:), eye(4), model.frameScale);
        drawFrame(hFr(2,:), Ttcp, model.frameScale);
        % 数据
        infoText.Value = splitlines(sprintf( ...
            'q[deg]=[%.1f %.1f %.1f %.1f]  TCP=[%.1f %.1f %.1f]  夹持宽=%.1f mm  rankJ=%d/%d  cond=%.3g', ...
            state.qDeg, pt, K.gripW, rank(J,1e-8), rank(J(1:3,:),1e-8), cond(J)));
        jText.Value = splitlines(sprintf('J0 [Jv;Jw] 6x4\n%s\n\n奇异值: %s', mat2str(J,4), mat2str(svd(J),4)));
        tText.Value = splitlines(sprintf(['TCP=%s\nPitch=%s  Roll=%s\nFingerA=%s  FingerB=%s  TipA=%s  TipB=%s\nContactA=%s  ContactB=%s'], ...
            vstr(pt),vstr(K.p2),vstr(K.p3),vstr(K.pFA),vstr(K.pFB),vstr(K.pTA),vstr(K.pTB),vstr(K.pCA),vstr(K.pCB)));
        drawnow limitrate;
    end
end

%% ===================== 运动学（TCP固定在Gripper上） =====================
function [J, K, Ttcp] = modelKin(q, m)
q1=q(1); q2=q(2); q3=q(3); g=q(4);
T01 = Rx(q1);
T_pitch = T01 * Tx(m.L12);
T02 = T_pitch * Ry(q2);
T_roll = T02 * Tx(m.L23);
T03 = T_roll * Rx(q3);            % Gripper 坐标系
% TCP 固定在 Gripper Body 上
pTcp = T03(1:3,4) + T03(1:3,1:3)*m.tcpOffsetInG;
Ttcp = [T03(1:3,1:3), pTcp; 0 0 0 1];
% 夹爪分支（用于显示接触点和动画）
qG = m.grip.coupling * g;
TA = T03 * Tr(m.grip.rootX, m.grip.rootY, 0) * Rz(qG(1));
TB = T03 * Tr(m.grip.rootX,-m.grip.rootY, 0) * Rz(qG(2));
TTA= TA * Tr(m.grip.linkX, m.grip.linkY, 0) * Rz(qG(3));
TTB= TB * Tr(m.grip.linkX,-m.grip.linkY, 0) * Rz(qG(4));
pCA = TTA(1:3,4) + TTA(1:3,1:3)*[m.grip.contactX;0;0];
pCB = TTB(1:3,4) + TTB(1:3,1:3)*[m.grip.contactX;0;0];
% 输出
K.T_wrBody = T01; K.T_wrRoll = T02; K.T_gripper = T03;
K.T_fA = TA; K.T_fB = TB; K.T_tA = TTA; K.T_tB = TTB;
K.p1 = [0;0;0];
K.p2 = T_pitch(1:3,4);
K.p3 = T_roll(1:3,4);
K.pFA = TA(1:3,4); K.pFB = TB(1:3,4);
K.pTA = TTA(1:3,4); K.pTB = TTB(1:3,4);
K.pCA = pCA; K.pCB = pCB;
K.pTCP = pTcp;
K.gripW = norm(pCA - pCB);
% 雅可比（TCP固定，第4列g为全零）
a1 = [1;0;0];
a2 = T01(1:3,1:3)*[0;1;0];
a3 = T02(1:3,1:3)*[1;0;0];
Jv1 = cross(a1, pTcp - K.p1);
Jv2 = cross(a2, pTcp - K.p2);
Jv3 = cross(a3, pTcp - K.p3);
J = [Jv1,Jv2,Jv3,[0;0;0]; a1,a2,a3,[0;0;0]];
end

function T = fkOnly(q, m)
[~,~,T] = modelKin(q, m);
end

function J = numJac(f, q)
h = 1e-7; n = numel(q); J = zeros(6,n);
T0 = f(q); R0 = T0(1:3,1:3);
for i = 1:n
    dq = zeros(n,1); dq(i) = h;
    Tp = f(q+dq); Tm = f(q-dq);
    J(1:3,i) = (Tp(1:3,4)-Tm(1:3,4))/(2*h);
    Rd = (Tp(1:3,1:3)-Tm(1:3,1:3))/(2*h);
    W = 0.5*(Rd*R0' - (Rd*R0').');
    J(4:6,i) = [W(3,2);W(1,3);W(2,1)];
end
end

%% ===================== IK（固定TCP，半径恒定177mm） =====================
function sol = ikFixedTCP(pTarget, m, opts)
% pTarget: 目标 TCP 位置 (3x1), mm
% 固定半径 L=177 mm，球心 C=[50;0;0]
if nargin < 3, opts = struct; end
if ~isfield(opts,'qCurrent'), opts.qCurrent = zeros(4,1); end
if ~isfield(opts,'positionOnly'), opts.positionOnly = true; end
if ~isfield(opts,'verbose'), opts.verbose = false; end

C = [m.L12; 0; 0];
d = pTarget - C;
Ltar = norm(d);
Lfix = m.L23 + m.grip.rootX + m.grip.linkX + m.grip.contactX + m.tcpOffsetInG(1) - m.L23;
% 简化：Lfix = 54+53+40 = 147 (相对 wrist roll)，+30 (roll→pitch) = 177
Lfix = 177;
% Actually let me use the explicit value
% tcpOffsetInG = [147;0;0], L23=30, so distance from pitch = 30+147 = 177 ✓

Q = []; errors = [];
if Ltar < 1e-9
    sol = struct('q',zeros(4,0),'errors',[],'message','目标在球心，方向不可定义');
    return;
end
% 投影到球面
p = C + Lfix * d / Ltar;
Lerr = abs(Ltar - Lfix);
c2 = (p(1) - m.L12) / Lfix;
c2 = max(-1, min(1, c2));
q2Cands = uniqueTol([acos(c2), -acos(c2)], 1e-10);
qCur = opts.qCurrent;

for i2 = 1:numel(q2Cands)
    q2 = wrapToPi(q2Cands(i2));
    if q2 < m.qlim(2,1)-1e-10 || q2 > m.qlim(2,2)+1e-10, continue; end
    s2 = sin(q2);
    if abs(s2) < 1e-9
        q1Cands = qCur(1);
    else
        q1Cands = atan2(p(2)/(Lfix*s2), -p(3)/(Lfix*s2));
    end
    for i1 = 1:numel(q1Cands)
        q1 = normToLim(q1Cands(i1), m.qlim(1,:));
        if isnan(q1), continue; end
        q3 = normToLim(qCur(3), m.qlim(3,:));
        if isnan(q3), q3 = 0; end
        q = [q1; q2; q3; qCur(4)];  % g保持当前值
        % 验证
        [~,K,~] = modelKin(q, m);
        pe = norm(K.pTCP - pTarget);
        if pe < 1e-6
            Q(:,end+1) = q;
            errors(end+1) = pe;
        end
    end
end

if isempty(Q)
    sol = struct('q',zeros(4,0),'errors',[],'message',sprintf('无解。目标半径=%.1f，需=%.1f，差值=%.1f mm', Ltar, Lfix, Lerr));
    return;
end
% 去重 + 距离排序
[Q, errors] = uniqueSol(Q, errors, qCur);
sol = struct('q',Q,'errors',errors,'message','');
if opts.verbose
    fprintf('IK: %d 组解\n', size(Q,2));
end
end

%% ===================== 工具函数 =====================
function drawFrame(h, T, s)
p = T(1:3,4); R = T(1:3,1:3);
for k = 1:3
    set(h(k),'XData',p(1),'YData',p(2),'ZData',p(3), ...
        'UData',s*R(1,k),'VData',s*R(2,k),'WData',s*R(3,k));
end
end

function [Q2, e2] = uniqueSol(Q, e, qCur)
if isempty(Q), Q2 = Q; e2 = e; return; end
% 去重
keep = true(1, size(Q,2));
for i = 1:size(Q,2)
    if ~keep(i), continue; end
    for j = i+1:size(Q,2)
        if norm(wrapToPi(Q(:,i)-Q(:,j))) < 1e-8, keep(j) = false; end
    end
end
Q = Q(:,keep); e = e(keep);
% 按离当前姿态最近排序
dist = zeros(1, size(Q,2));
for i = 1:size(Q,2)
    dq = Q(:,i) - qCur;
    dq(1:3) = wrapToPi(dq(1:3));
    dist(i) = norm(dq);
end
[~,idx] = sort(dist);
Q2 = Q(:,idx); e2 = e(idx);
end

function a = uniqueTol(a, tol)
if isempty(a), return; end
a = sort(a(:)');
keep = [true, abs(diff(a)) > tol];
a = a(keep);
end

function q = normToLim(qr, lim)
c = qr + 2*pi*(-2:2);
v = c(c >= lim(1)-1e-10 & c <= lim(2)+1e-10);
if isempty(v), q = NaN; else, [~,i] = min(abs(v-qr)); q = v(i); end
end

function x = wrapToPi(x)
x = mod(x+pi, 2*pi) - pi;
end

function s = vstr(v)
s = sprintf('[%.1f %.1f %.1f]', v(1), v(2), v(3));
end

function T = Rx(q), c=cos(q);s=sin(q);T=[1 0 0 0;0 c -s 0;0 s c 0;0 0 0 1]; end
function T = Ry(q), c=cos(q);s=sin(q);T=[c 0 s 0;0 1 0 0;-s 0 c 0;0 0 0 1]; end
function T = Rz(q), c=cos(q);s=sin(q);T=[c -s 0 0;s c 0 0;0 0 1 0;0 0 0 1]; end
function T = Tx(x), T=eye(4);T(1,4)=x; end
function T = Tr(x,y,z), T=eye(4);T(1:3,4)=[x;y;z]; end
