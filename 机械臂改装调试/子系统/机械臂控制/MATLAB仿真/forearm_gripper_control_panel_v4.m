function forearm_gripper_control_panel_v4
% FOREARM_GRIPPER_CONTROL_PANEL_V4
% 前臂-腕部-平行四边形夹爪：正/逆运动学交互实验平台。
%
% 相比 V2 新增：
%   - “逆解IK”标签页
%   - 位置 IK：自动求 g / 固定当前 g / 手动 g
%   - 固定 g 不在球面时自动投影到最近可达点
%   - 候选解表格、推荐解应用、目标点/投影点可视化
%
% 坐标：世界原点在袖筒与第一旋转基座连接处，袖筒固定。
% 单位：长度 mm；界面角度 deg；内部角度 rad。

%% 1. 模型参数
model.stlDir = 'D:\假肢机械臂\机械臂改装调试\原始资料\STL模型\stl_files';
assert(isfolder(model.stlDir), '找不到 STL 文件夹：%s', model.stlDir);

model.L12 = 50;
model.L23 = 30;
model.grip.rootX = 54;
model.grip.rootY = 6;
model.grip.linkX = 53;
model.grip.linkY = 2;
model.grip.contactX = 40;
model.grip.coupling = [1;-1;-1;1]; % qA=+g, qB=-g, qTipA=-g, qTipB=+g
model.qlimDeg = [-180 180; -90 15; -180 180; 0 90];
model.qlim = deg2rad(model.qlimDeg);
model.names = {'q1 前臂旋转','q2 腕部俯仰','q3 腕部滚转','g 夹爪开合'};
model.maxMeshFaces = 25000;
model.frameScale = 24;
model.axisLength = [90,90,90,55,55,45,45];
model.wsFastN = [37,22,13];
model.wsSliceN = [73,43];

%% 2. 读取 STL
files = {'socket.stl','wrsit_body.stl','wrist_roll.stl','gripper_body.stl', ...
         'finger_body_a.stl','finger_body_b.stl','fingertip_a.stl','fingertip_b.stl'};
keys = {'socket','wristBody','wristRoll','gripper','fingerA','fingerB','tipA','tipB'};
colors = [0.35 0.35 0.38; 0.20 0.48 0.80; 0.25 0.68 0.72; 0.85 0.55 0.18; ...
          0.82 0.25 0.22; 0.82 0.25 0.22; 0.95 0.72 0.25; 0.95 0.72 0.25];
mesh = struct;
for i = 1:numel(files)
    fn = fullfile(model.stlDir, files{i});
    assert(isfile(fn), '缺少 STL 文件：%s', fn);
    TR = stlread(fn);
    F = TR.ConnectivityList; V = TR.Points;
    if size(F,1) > model.maxMeshFaces
        [F,V] = reducepatch(F,V,model.maxMeshFaces);
    end
    mesh.(keys{i}) = struct('F',F,'V',V,'color',colors(i,:));
end

%% 3. 状态
state.qDeg = [0;0;0;0];
state.track = zeros(0,3);
state.wsMode = '隐藏';
state.wsPoints = zeros(0,3);
state.lastIK = struct('q',zeros(4,0),'rows',{{}},'message','尚未求解');
state.targetPoint = [nan;nan;nan];
state.usedPoint = [nan;nan;nan];

%% 4. UI
fig = uifigure('Name','前臂-腕部-夹爪 正逆运动学实验平台 V4', ...
    'Position',[35 35 1540 920], 'Color',[0.96 0.97 0.98]);
main = uigridlayout(fig,[1 2]);
main.ColumnWidth = {1000,'1x'};
main.Padding = [8 8 8 8]; main.ColumnSpacing = 8;

ax = uiaxes(main); ax.Layout.Column = 1;
hold(ax,'on'); grid(ax,'on'); axis(ax,'equal'); axis(ax,'vis3d');
xlabel(ax,'X / mm'); ylabel(ax,'Y / mm'); zlabel(ax,'Z / mm');
title(ax,'Forearm-Gripper Kinematics V4'); view(ax,35,25);
ax.XLim=[-240 290]; ax.YLim=[-270 270]; ax.ZLim=[-270 270];

right = uitabgroup(main); right.Layout.Column = 2;
tabControl = uitab(right,'Title','关节/显示');
tabIK = uitab(right,'Title','逆解 IK');
tabData = uitab(right,'Title','中间数据');

%% 4.1 关节/显示页
ctrlGrid = uigridlayout(tabControl,[3 1]);
ctrlGrid.RowHeight = {292,220,'1x'}; ctrlGrid.Padding=[6 6 6 6];

pJoint = uipanel(ctrlGrid,'Title','关节控制（deg）','FontWeight','bold');
gJoint = uigridlayout(pJoint,[6 4]);
gJoint.RowHeight={38,38,38,38,38,'1x'}; gJoint.ColumnWidth={115,'1x',80,70};
slider = gobjects(4,1); field = gobjects(4,1);
for i=1:4
    uilabel(gJoint,'Text',model.names{i});
    slider(i)=uislider(gJoint,'Limits',model.qlimDeg(i,:), 'Value',state.qDeg(i), ...
        'MajorTicks',linspace(model.qlimDeg(i,1),model.qlimDeg(i,2),5));
    field(i)=uieditfield(gJoint,'numeric','Limits',model.qlimDeg(i,:), ...
        'Value',state.qDeg(i),'ValueDisplayFormat','%.3f');
    uilabel(gJoint,'Text',sprintf('[%g,%g]',model.qlimDeg(i,:)),'HorizontalAlignment','center');
    slider(i).ValueChangingFcn = @(~,e)sliderMove(i,e.Value);
    slider(i).ValueChangedFcn = @(~,e)sliderDone(i,e.Value);
    field(i).ValueChangedFcn = @(~,e)fieldDone(i,e.Value);
end
uibutton(gJoint,'Text','全部回零','ButtonPushedFcn',@(~,~)setPose([0;0;0;0]));
uibutton(gJoint,'Text','随机姿态','ButtonPushedFcn',@(~,~)setRandomPose());
uibutton(gJoint,'Text','清轨迹','ButtonPushedFcn',@(~,~)clearTrack());
uibutton(gJoint,'Text','雅可比验证','ButtonPushedFcn',@(~,~)checkJacobian());

pShow = uipanel(ctrlGrid,'Title','显示与工作空间','FontWeight','bold');
gShow = uigridlayout(pShow,[5 4]);
gShow.RowHeight={32,32,32,32,'1x'};
cbSTL = uicheckbox(gShow,'Text','STL','Value',true,'ValueChangedFcn',@(~,~)applyVisibility());
cbSkeleton = uicheckbox(gShow,'Text','骨架','Value',true,'ValueChangedFcn',@(~,~)applyVisibility());
cbAxis = uicheckbox(gShow,'Text','关节轴','Value',true,'ValueChangedFcn',@(~,~)applyVisibility());
cbFrame = uicheckbox(gShow,'Text','坐标系','Value',true,'ValueChangedFcn',@(~,~)applyVisibility());
cbTCP = uicheckbox(gShow,'Text','TCP/接触点','Value',true,'ValueChangedFcn',@(~,~)applyVisibility());
cbTrack = uicheckbox(gShow,'Text','TCP轨迹','Value',true,'ValueChangedFcn',@(~,~)applyVisibility());
cbAutoTrack = uicheckbox(gShow,'Text','记录轨迹','Value',true);
cbAlpha = uicheckbox(gShow,'Text','半透明','Value',false,'ValueChangedFcn',@(~,~)applyVisibility());
uilabel(gShow,'Text','工作空间');
ddWS = uidropdown(gShow,'Items',{'隐藏','全部理论范围','当前 g 切片'},'Value','隐藏','ValueChangedFcn',@(~,~)workspaceChanged());
ddWS.Layout.Column=[2 3];
uibutton(gShow,'Text','刷新','ButtonPushedFcn',@(~,~)computeWorkspace());
uilabel(gShow,'Text','说明：q3 只改姿态，不改 TCP 位置。');
uilabel(gShow,'Text','固定 g 时 TCP 在球面带上；g 可变时为球壳带。');

summaryText = uitextarea(ctrlGrid,'Editable','off','FontName','Consolas','FontSize',12);

%% 4.2 IK 页
ikGrid = uigridlayout(tabIK,[5 1]);
ikGrid.RowHeight = {168,102,150,170,'1x'}; ikGrid.Padding=[6 6 6 6];

pTarget = uipanel(ikGrid,'Title','目标输入','FontWeight','bold');
gTarget = uigridlayout(pTarget,[4 4]);
gTarget.RowHeight={32,32,32,'1x'}; gTarget.ColumnWidth={80,'1x',90,'1x'};
uilabel(gTarget,'Text','目标 X'); ikX = uieditfield(gTarget,'numeric','Value',227,'ValueDisplayFormat','%.4f');
uilabel(gTarget,'Text','目标 Y'); ikY = uieditfield(gTarget,'numeric','Value',0,'ValueDisplayFormat','%.4f');
uilabel(gTarget,'Text','目标 Z'); ikZ = uieditfield(gTarget,'numeric','Value',0,'ValueDisplayFormat','%.4f');
uilabel(gTarget,'Text','q3/滚转'); ikQ3 = uieditfield(gTarget,'numeric','Value',0,'Limits',model.qlimDeg(3,:),'ValueDisplayFormat','%.3f');
uilabel(gTarget,'Text','g 模式'); ikMode = uidropdown(gTarget,'Items',{'自动求 g','固定当前 g','手动 g'},'Value','自动求 g');
uilabel(gTarget,'Text','手动 g'); ikG = uieditfield(gTarget,'numeric','Value',0,'Limits',model.qlimDeg(4,:),'ValueDisplayFormat','%.3f');

pButtons = uipanel(ikGrid,'Title','求解操作','FontWeight','bold');
gButtons = uigridlayout(pButtons,[2 4]);
uibutton(gButtons,'Text','读取当前TCP','ButtonPushedFcn',@(~,~)readCurrentTCP());
uibutton(gButtons,'Text','预览目标点','ButtonPushedFcn',@(~,~)previewTarget());
uibutton(gButtons,'Text','解析位置IK','ButtonPushedFcn',@(~,~)solveIK());
uibutton(gButtons,'Text','应用推荐解','ButtonPushedFcn',@(~,~)applyIK(1));
uilabel(gButtons,'Text','应用编号'); applyIndex = uieditfield(gButtons,'numeric','Value',1,'Limits',[1 Inf],'RoundFractionalValues','on');
uibutton(gButtons,'Text','应用指定编号','ButtonPushedFcn',@(~,~)applyIK(applyIndex.Value));
uibutton(gButtons,'Text','清除目标/投影','ButtonPushedFcn',@(~,~)clearIKGraphics());
uibutton(gButtons,'Text','说明','ButtonPushedFcn',@(~,~)showIKHelp());

ikResultText = uitextarea(ikGrid,'Editable','off','FontName','Consolas','FontSize',12);
ikTable = uitable(ikGrid,'ColumnName',{'#','q1','q2','q3','g','posErr','投影误差','dist'}, ...
    'ColumnWidth',{35,58,58,58,58,80,80,70});

ikExplain = uitextarea(ikGrid,'Editable','off','FontName','Consolas','FontSize',11);
ikExplain.Value = splitlines(sprintf(['逆解模式说明\n', ...
    '1) 自动求 g：目标半径决定夹爪开度 g，适合探索总工作空间。\n', ...
    '2) 固定当前 g：保持当前夹爪开度；若目标不在球面上，自动投影到最近可达点。\n', ...
    '3) 手动 g：使用输入的 g；同样可投影。\n', ...
    '当前 IK 是“位置 IK + 指定 q3滚转”，不是任意 6D 位姿 IK。']));

%% 4.3 数据页
dataTabs = uitabgroup(tabData,'Position',[5 5 500 850]);
tabState = uitab(dataTabs,'Title','状态');
tabJ = uitab(dataTabs,'Title','雅可比');
tabT = uitab(dataTabs,'Title','变换/点');
stateText = uitextarea(tabState,'Editable','off','FontName','Consolas','FontSize',12,'Position',[5 5 485 800]);
jText = uitextarea(tabJ,'Editable','off','FontName','Consolas','FontSize',11,'Position',[5 5 485 800]);
tText = uitextarea(tabT,'Editable','off','FontName','Consolas','FontSize',11,'Position',[5 5 485 800]);

%% 5. 图元
hT=struct; hPatch=struct;
for i=1:numel(keys)
    hT.(keys{i}) = hgtransform(ax);
    M = mesh.(keys{i});
    hPatch.(keys{i}) = patch(ax,'Faces',M.F,'Vertices',M.V,'Parent',hT.(keys{i}), ...
        'FaceColor',M.color,'EdgeColor','none','AmbientStrength',0.35, ...
        'DiffuseStrength',0.75,'SpecularStrength',0.12);
end
hSkeleton(1)=plot3(ax,nan,nan,nan,'k.-','LineWidth',2,'MarkerSize',18);
hSkeleton(2)=plot3(ax,nan,nan,nan,'m.-','LineWidth',2,'MarkerSize',16);
hSkeleton(3)=plot3(ax,nan,nan,nan,'m.-','LineWidth',2,'MarkerSize',16);
axisColors={[.8 .1 .1],[.1 .65 .1],[.8 .1 .1],[.1 .25 .9],[.1 .25 .9],[.15 .45 1],[.15 .45 1]};
hAxes=gobjects(7,1);
for i=1:7, hAxes(i)=plot3(ax,nan,nan,nan,'--','Color',axisColors{i},'LineWidth',1.8); end
hFrames=gobjects(4,3);
for i=1:4
    hFrames(i,1)=quiver3(ax,0,0,0,0,0,0,0,'r','LineWidth',1.5);
    hFrames(i,2)=quiver3(ax,0,0,0,0,0,0,0,'g','LineWidth',1.5);
    hFrames(i,3)=quiver3(ax,0,0,0,0,0,0,0,'b','LineWidth',1.5);
end
hTCP=plot3(ax,nan,nan,nan,'kp','MarkerFaceColor','y','MarkerSize',13);
hContacts=plot3(ax,nan,nan,nan,'co','MarkerFaceColor','c','MarkerSize',8);
hTrack=plot3(ax,nan,nan,nan,'Color',[0.55 0 0.75],'LineWidth',1.6);
hWorkspace=scatter3(ax,nan,nan,nan,5,[0.15 .55 .95],'filled','MarkerFaceAlpha',0.16);
hTarget=plot3(ax,nan,nan,nan,'rx','LineWidth',2.4,'MarkerSize',13);
hUsed=plot3(ax,nan,nan,nan,'go','LineWidth',2.0,'MarkerSize',10);
camlight(ax,'headlight'); lighting(ax,'gouraud');

updateAll(false);

%% ===================== 回调函数 =====================
    function sliderMove(i,val), state.qDeg(i)=val; field(i).Value=val; updateAll(true); end
    function sliderDone(i,val), state.qDeg(i)=val; field(i).Value=val; updateAll(true); end
    function fieldDone(i,val), state.qDeg(i)=val; slider(i).Value=val; updateAll(true); end
    function setPose(qDeg)
        state.qDeg=qDeg(:);
        for k=1:4, slider(k).Value=state.qDeg(k); field(k).Value=state.qDeg(k); end
        updateAll(true);
    end
    function setRandomPose()
        lo=model.qlimDeg(:,1); hi=model.qlimDeg(:,2);
        setPose(lo+(hi-lo).*rand(4,1));
    end
    function clearTrack()
        state.track=zeros(0,3); set(hTrack,'XData',nan,'YData',nan,'ZData',nan);
    end
    function checkJacobian()
        q=deg2rad(state.qDeg);
        [J,~,~]=modelKinematics(q,model);
        Jn=numericalJacobian(@(qq)modelKinematicsOnly(qq,model),q);
        D=J-Jn;
        uialert(fig,sprintf('Frobenius误差 = %.3e\n最大元素误差 = %.3e',norm(D,'fro'),max(abs(D),[],'all')),'雅可比中心差分验证');
    end
    function workspaceChanged(), state.wsMode=ddWS.Value; computeWorkspace(); end
    function computeWorkspace()
        state.wsMode=ddWS.Value;
        switch state.wsMode
            case '隐藏'
                state.wsPoints=zeros(0,3);
            case '全部理论范围'
                state.wsPoints=sampleWorkspace(model,model.wsFastN,[]);
            case '当前 g 切片'
                state.wsPoints=sampleWorkspace(model,model.wsSliceN,deg2rad(state.qDeg(4)));
        end
        if isempty(state.wsPoints), set(hWorkspace,'XData',nan,'YData',nan,'ZData',nan);
        else, set(hWorkspace,'XData',state.wsPoints(:,1),'YData',state.wsPoints(:,2),'ZData',state.wsPoints(:,3)); end
        applyVisibility();
    end
    function readCurrentTCP()
        q=deg2rad(state.qDeg); [~,~,T]=modelKinematics(q,model); p=T(1:3,4);
        ikX.Value=p(1); ikY.Value=p(2); ikZ.Value=p(3); ikQ3.Value=state.qDeg(3); ikG.Value=state.qDeg(4);
        previewTarget();
    end
    function previewTarget()
        p=[ikX.Value;ikY.Value;ikZ.Value]; state.targetPoint=p; state.usedPoint=[nan;nan;nan];
        set(hTarget,'XData',p(1),'YData',p(2),'ZData',p(3));
        set(hUsed,'XData',nan,'YData',nan,'ZData',nan);
    end
    function clearIKGraphics()
        state.targetPoint=[nan;nan;nan]; state.usedPoint=[nan;nan;nan];
        state.lastIK=struct('q',zeros(4,0),'rows',{{}},'message','已清除');
        set(hTarget,'XData',nan,'YData',nan,'ZData',nan);
        set(hUsed,'XData',nan,'YData',nan,'ZData',nan);
        ikTable.Data={}; ikResultText.Value={'已清除目标和候选解'};
    end
    function solveIK()
        p=[ikX.Value;ikY.Value;ikZ.Value]; q3des=deg2rad(ikQ3.Value);
        mode=ikMode.Value; qCurrent=deg2rad(state.qDeg);
        switch mode
            case '自动求 g'
                gMode='auto'; gInput=[];
            case '固定当前 g'
                gMode='fixed'; gInput=qCurrent(4);
            case '手动 g'
                gMode='manual'; gInput=deg2rad(ikG.Value);
            otherwise
                gMode='auto'; gInput=[];
        end
        opts.qCurrent=qCurrent; opts.q3Desired=q3des; opts.gMode=gMode; opts.gInput=gInput;
        sol=ikPositionV4(p,model,opts);
        state.lastIK=sol;
        state.targetPoint=p;
        if all(isfinite(sol.pUsed)), state.usedPoint=sol.pUsed; else, state.usedPoint=[nan;nan;nan]; end
        set(hTarget,'XData',p(1),'YData',p(2),'ZData',p(3));
        if all(isfinite(state.usedPoint))
            set(hUsed,'XData',state.usedPoint(1),'YData',state.usedPoint(2),'ZData',state.usedPoint(3));
        else
            set(hUsed,'XData',nan,'YData',nan,'ZData',nan);
        end
        ikResultText.Value=splitlines(sol.message);
        ikTable.Data=sol.rows;
    end
    function applyIK(idx)
        idx=round(idx);
        if isempty(state.lastIK.q)
            uialert(fig,'当前没有可应用的 IK 解，请先求解。','无候选解'); return;
        end
        if idx<1 || idx>size(state.lastIK.q,2)
            uialert(fig,sprintf('编号必须在 1 到 %d 之间。',size(state.lastIK.q,2)),'编号无效'); return;
        end
        setPose(rad2deg(state.lastIK.q(:,idx)));
    end
    function showIKHelp()
        uialert(fig, sprintf(['当前 IK 是位置逆解：求 q1,q2,g，并使用指定 q3。\n\n', ...
            '固定 g 时 TCP 必须在对应球面上；程序会把目标点投影到该球面并显示投影误差。\n\n', ...
            '完整 6D 位姿 IK 不是任意可解，因为本机构只有 4 个主动自由度。']), 'IK 说明');
    end
    function updateAll(recordTrack)
        q=deg2rad(state.qDeg);
        [J,K,Ttcp]=modelKinematics(q,model);
        hT.socket.Matrix=eye(4); hT.wristBody.Matrix=K.T_wristBody; hT.wristRoll.Matrix=K.T_wristRoll;
        hT.gripper.Matrix=K.T_gripper; hT.fingerA.Matrix=K.T_fingerA; hT.fingerB.Matrix=K.T_fingerB; hT.tipA.Matrix=K.T_tipA; hT.tipB.Matrix=K.T_tipB;
        set(hSkeleton(1),'XData',[K.p1(1),K.p2(1),K.p3(1)],'YData',[K.p1(2),K.p2(2),K.p3(2)],'ZData',[K.p1(3),K.p2(3),K.p3(3)]);
        set(hSkeleton(2),'XData',[K.p3(1),K.pFingerA(1),K.pTipA(1),K.pContactA(1)],'YData',[K.p3(2),K.pFingerA(2),K.pTipA(2),K.pContactA(2)],'ZData',[K.p3(3),K.pFingerA(3),K.pTipA(3),K.pContactA(3)]);
        set(hSkeleton(3),'XData',[K.p3(1),K.pFingerB(1),K.pTipB(1),K.pContactB(1)],'YData',[K.p3(2),K.pFingerB(2),K.pTipB(2),K.pContactB(2)],'ZData',[K.p3(3),K.pFingerB(3),K.pTipB(3),K.pContactB(3)]);
        pts={K.p1,K.p2,K.p3,K.pFingerA,K.pFingerB,K.pTipA,K.pTipB};
        dirs={K.a1,K.a2,K.a3,K.aGripZ,K.aGripZ,K.aFingerAZ,K.aFingerBZ};
        for kk=1:7, setAxisLine(hAxes(kk),pts{kk},dirs{kk},model.axisLength(kk)); end
        frames={eye(4),K.T_pitch,K.T_gripper,Ttcp};
        for kk=1:4, setFrameGraphics(hFrames(kk,:),frames{kk},model.frameScale); end
        p=Ttcp(1:3,4);
        set(hTCP,'XData',p(1),'YData',p(2),'ZData',p(3));
        set(hContacts,'XData',[K.pContactA(1),K.pContactB(1)],'YData',[K.pContactA(2),K.pContactB(2)],'ZData',[K.pContactA(3),K.pContactB(3)]);
        if recordTrack && cbAutoTrack.Value
            state.track(end+1,:)=p.'; if size(state.track,1)>3000, state.track=state.track(end-2999:end,:); end
        end
        if isempty(state.track), set(hTrack,'XData',nan,'YData',nan,'ZData',nan);
        else, set(hTrack,'XData',state.track(:,1),'YData',state.track(:,2),'ZData',state.track(:,3)); end
        updateTexts(J,K,Ttcp);
        applyVisibility(); drawnow limitrate;
    end
    function updateTexts(J,K,Ttcp)
        p=Ttcp(1:3,4); sv=svd(J); rankJ=rank(J,1e-8); rankV=rank(J(1:3,:),1e-8); cJ=cond(J);
        qActual=rad2deg(K.qGrip);
        summaryText.Value=splitlines(sprintf(['当前 q[deg]=[%.2f %.2f %.2f %.2f]\n', ...
            'TCP=[%.3f %.3f %.3f] mm\n夹持宽度=%.3f mm\nrank(J)=%d rank(Jv)=%d cond(J)=%.4g'], ...
            state.qDeg,p,K.gripWidth,rankJ,rankV,cJ));
        stateText.Value=splitlines(sprintf(['主动变量 [deg]\n q1=%9.3f  q2=%9.3f\n q3=%9.3f  g =%9.3f\n\n', ...
            '受约束夹爪角 [deg]\n A=%9.3f  B=%9.3f\n TipA=%6.3f  TipB=%6.3f\n\n', ...
            'TCP [mm]\n x=%10.4f\n y=%10.4f\n z=%10.4f\n\n夹持宽度 = %.4f mm\n相对Pitch半径 = %.4f mm\n相对Roll距离 = %.4f mm'], ...
            state.qDeg(1),state.qDeg(2),state.qDeg(3),state.qDeg(4),qActual(1),qActual(2),qActual(3),qActual(4),p,K.gripWidth,norm(p-[model.L12;0;0]),K.tcpRadius));
        jText.Value=splitlines(sprintf(['J0=[Jv;Jw] 6x4\n%s\n\nrank(J)=%d rank(Jv)=%d\ncond(J)=%.5g\n奇异值=%s\n\n列顺序：[q1 q2 q3 g]'], ...
            mat2str(J,5),rankJ,rankV,cJ,mat2str(sv,5)));
        tText.Value=splitlines(sprintf(['T0_TCP=\n%s\n\nPitch %s\nRoll  %s\nFingerA %s\nFingerB %s\nTipA %s\nTipB %s\nContactA %s\nContactB %s'], ...
            mat2str(Ttcp,5),vstr(K.p2),vstr(K.p3),vstr(K.pFingerA),vstr(K.pFingerB),vstr(K.pTipA),vstr(K.pTipB),vstr(K.pContactA),vstr(K.pContactB)));
    end
    function applyVisibility()
        patches=[hPatch.socket,hPatch.wristBody,hPatch.wristRoll,hPatch.gripper,hPatch.fingerA,hPatch.fingerB,hPatch.tipA,hPatch.tipB];
        set(patches,'Visible',onOff(cbSTL.Value));
        if cbAlpha.Value, a=0.38; else, a=1.0; end
        set(patches,'FaceAlpha',a);
        set(hSkeleton,'Visible',onOff(cbSkeleton.Value)); set(hAxes,'Visible',onOff(cbAxis.Value)); set(hFrames(:),'Visible',onOff(cbFrame.Value));
        set([hTCP,hContacts],'Visible',onOff(cbTCP.Value)); set(hTrack,'Visible',onOff(cbTrack.Value));
        showWs=~strcmp(state.wsMode,'隐藏') && ~isempty(state.wsPoints); set(hWorkspace,'Visible',onOff(showWs));
        set([hTarget,hUsed],'Visible','on');
    end
end

%% ===================== IK =====================
function sol=ikPositionV4(pTarget,m,opts)
qCur=opts.qCurrent; q3=normalizeToLimit(opts.q3Desired,m.qlim(3,:));
if isnan(q3)
    sol=makeIKSol([],{},'指定 q3 超出限位。',[nan;nan;nan],[nan;nan;nan]); return;
end
C=[m.L12;0;0]; d=pTarget-C; Ltar=norm(d);
Lmin=radiusFromG(m.qlim(4,2),m); Lmax=radiusFromG(m.qlim(4,1),m);
msg=sprintf('目标半径 L=%.4f mm；理论半径范围 [%.4f, %.4f] mm\n',Ltar,Lmin,Lmax);
Q=[]; rows={}; pUsed=pTarget; projectionErr=0;
if Ltar<1e-9
    sol=makeIKSol([],{},[msg,'目标点与 Pitch 中心重合，方向不可定义。'],pTarget,[nan;nan;nan]); return;
end
switch opts.gMode
    case 'auto'
        gList=solveGFromRadius(Ltar,m);
        if isempty(gList)
            sol=makeIKSol([],{},[msg,'自动 g 失败：目标半径不在夹爪可调范围内。'],pTarget,[nan;nan;nan]); return;
        end
        msg=[msg,sprintf('自动 g 候选数量：%d\n',numel(gList))]; %#ok<AGROW>
    case {'fixed','manual'}
        g0=opts.gInput;
        if g0<m.qlim(4,1)-1e-10 || g0>m.qlim(4,2)+1e-10
            sol=makeIKSol([],{},[msg,'指定 g 超出 PDF 限位。'],pTarget,[nan;nan;nan]); return;
        end
        Lg=radiusFromG(g0,m);
        pUsed=C + Lg*d/Ltar;
        projectionErr=norm(pUsed-pTarget);
        gList=g0;
        msg=[msg,sprintf('固定/手动 g=%.3f deg，半径 L(g)=%.4f mm，投影误差=%.4f mm\n',rad2deg(g0),Lg,projectionErr)]; %#ok<AGROW>
    otherwise
        sol=makeIKSol([],{},[msg,'未知 g 模式。'],pTarget,[nan;nan;nan]); return;
end

for ig=1:numel(gList)
    g=gList(ig); L=radiusFromG(g,m); pSolve=pUsed;
    c2=(pSolve(1)-m.L12)/L; c2=min(1,max(-1,c2));
    q2cands=uniqueTol([acos(c2),-acos(c2)],1e-10);
    for i2=1:numel(q2cands)
        q2=wrapToPiLocal(q2cands(i2));
        if ~inLimit(q2,m.qlim(2,:)), continue; end
        s2=sin(q2);
        if abs(s2)<1e-9
            q1cands=qCur(1);
        else
            q1cands=atan2(pSolve(2)/(L*s2), -pSolve(3)/(L*s2));
        end
        for i1=1:numel(q1cands)
            q1=normalizeToLimit(q1cands(i1),m.qlim(1,:));
            if isnan(q1), continue; end
            q=[q1;q2;q3;g];
            [T,~]=modelKinematicsOnly(q,m); %#ok<ASGLU>
            posErr=norm(T(1:3,4)-pSolve);
            dist=jointDistance(q,qCur);
            if posErr<1e-6
                Q(:,end+1)=q; %#ok<AGROW>
                rows(end+1,:)={size(Q,2),rad2deg(q1),rad2deg(q2),rad2deg(q3),rad2deg(g),posErr,projectionErr,dist}; %#ok<AGROW>
            end
        end
    end
end
if isempty(Q)
    sol=makeIKSol([],{},[msg,'没有通过限位和误差检查的候选解。'],pTarget,pUsed); return;
end
[Q,rows]=sortIKRows(Q,rows);
msg=[msg,sprintf('IK 成功：%d 组候选解。表中第 1 行是推荐解。\n',size(Q,2))];
if projectionErr>1e-6
    msg=[msg,'注意：绿色圆点是实际用于求解的投影点，红叉是原目标点。'];
end
sol=makeIKSol(Q,rows,msg,pTarget,pUsed);
end

function sol=makeIKSol(Q,rows,msg,pTarget,pUsed)
if isempty(Q), Q=zeros(4,0); end
sol.q=Q; sol.rows=rows; sol.message=msg; sol.pTarget=pTarget; sol.pUsed=pUsed;
end

function [Q2,rows2]=sortIKRows(Q,rows)
if isempty(Q), Q2=Q; rows2=rows; return; end
dist=cell2mat(rows(:,8)); [~,idx]=sort(dist); Q2=Q(:,idx); rows2=rows(idx,:);
for i=1:size(rows2,1), rows2{i,1}=i; end
end

function gList=solveGFromRadius(L,m)
base=m.L23+m.grip.rootX+m.grip.contactX; A=m.grip.linkX; B=-m.grip.linkY;
R=hypot(A,B); alpha=atan2(B,A); y=(L-base)/R;
if y<-1-1e-10 || y>1+1e-10, gList=[]; return; end
y=min(1,max(-1,y)); raw=[alpha+acos(y),alpha-acos(y)]; raw=[raw,raw+2*pi,raw-2*pi];
gList=[];
for k=1:numel(raw)
    g=raw(k);
    if inLimit(g,m.qlim(4,:)) && abs(radiusFromG(g,m)-L)<1e-7
        gList(end+1)=g; %#ok<AGROW>
    end
end
gList=uniqueTol(gList,1e-10);
end

function L=radiusFromG(g,m)
L=m.L23+m.grip.rootX+m.grip.linkX*cos(g)-m.grip.linkY*sin(g)+m.grip.contactX;
end

%% ===================== 运动学核心 =====================
function [J,K,Ttcp]=modelKinematics(q,m)
q1=q(1); q2=q(2); q3=q(3); g=q(4);
T01=Rx(q1); T_pitch=T01*Tx(m.L12); T02=T_pitch*Ry(q2); T_roll=T02*Tx(m.L23); T03=T_roll*Rx(q3);
qGrip=m.grip.coupling*g;
TA=T03*Tr(m.grip.rootX,m.grip.rootY,0)*Rz(qGrip(1));
TB=T03*Tr(m.grip.rootX,-m.grip.rootY,0)*Rz(qGrip(2));
TTA=TA*Tr(m.grip.linkX,m.grip.linkY,0)*Rz(qGrip(3));
TTB=TB*Tr(m.grip.linkX,-m.grip.linkY,0)*Rz(qGrip(4));
pCA=TTA(1:3,4)+TTA(1:3,1:3)*[m.grip.contactX;0;0];
pCB=TTB(1:3,4)+TTB(1:3,1:3)*[m.grip.contactX;0;0];
pTCP=0.5*(pCA+pCB); Ttcp=[T03(1:3,1:3),pTCP;0 0 0 1];
K.T_wristBody=T01; K.T_pitch=T_pitch; K.T_wristRoll=T02; K.T_gripper=T03; K.T03=T03;
K.T_fingerA=TA; K.T_fingerB=TB; K.T_tipA=TTA; K.T_tipB=TTB;
K.p1=[0;0;0]; K.p2=T_pitch(1:3,4); K.p3=T_roll(1:3,4); K.pFingerA=TA(1:3,4); K.pFingerB=TB(1:3,4); K.pTipA=TTA(1:3,4); K.pTipB=TTB(1:3,4);
K.pContactA=pCA; K.pContactB=pCB; K.qGrip=qGrip;
K.a1=[1;0;0]; K.a2=T01(1:3,1:3)*[0;1;0]; K.a3=T02(1:3,1:3)*[1;0;0];
K.aGripZ=T03(1:3,1:3)*[0;0;1]; K.aFingerAZ=TA(1:3,1:3)*[0;0;1]; K.aFingerBZ=TB(1:3,1:3)*[0;0;1];
K.gripWidth=norm(pCA-pCB); K.tcpRadius=norm(pTCP-K.p3);
p=pTCP; Jv1=cross(K.a1,p-K.p1); Jv2=cross(K.a2,p-K.p2); Jv3=cross(K.a3,p-K.p3);
dx=-m.grip.linkX*sin(g)-m.grip.linkY*cos(g); Jv4=T03(1:3,1:3)*[dx;0;0];
J=[Jv1,Jv2,Jv3,Jv4; K.a1,K.a2,K.a3,[0;0;0]];
end

function T=modelKinematicsOnly(q,m)
[~,~,T]=modelKinematics(q,m);
end

function J=numericalJacobian(f,q)
h=1e-7; n=numel(q); J=zeros(6,n); T0=f(q); R0=T0(1:3,1:3);
for i=1:n
    d=zeros(n,1); d(i)=h; Tp=f(q+d); Tm=f(q-d);
    J(1:3,i)=(Tp(1:3,4)-Tm(1:3,4))/(2*h);
    Rdot=(Tp(1:3,1:3)-Tm(1:3,1:3))/(2*h);
    W=0.5*(Rdot*R0.'-(Rdot*R0.').');
    J(4:6,i)=[W(3,2);W(1,3);W(2,1)];
end
end

function P=sampleWorkspace(m,N,fixedG)
q1=linspace(m.qlimDeg(1,1),m.qlimDeg(1,2),N(1));
q2=linspace(m.qlimDeg(2,1),m.qlimDeg(2,2),N(2));
if isempty(fixedG), gv=linspace(m.qlimDeg(4,1),m.qlimDeg(4,2),N(3)); else, gv=rad2deg(fixedG); end
[Q1,Q2,G]=ndgrid(deg2rad(q1),deg2rad(q2),deg2rad(gv));
L=m.L23+m.grip.rootX+m.grip.linkX.*cos(G)-m.grip.linkY.*sin(G)+m.grip.contactX;
X=m.L12+L.*cos(Q2); Y=L.*sin(Q1).*sin(Q2); Z=-L.*cos(Q1).*sin(Q2);
P=[X(:),Y(:),Z(:)];
end

%% ===================== 小工具 =====================
function setAxisLine(h,p,a,L), a=a/norm(a); p0=p-.5*L*a; p1=p+.5*L*a; set(h,'XData',[p0(1),p1(1)],'YData',[p0(2),p1(2)],'ZData',[p0(3),p1(3)]); end
function setFrameGraphics(h,T,s), p=T(1:3,4); R=T(1:3,1:3); for k=1:3, set(h(k),'XData',p(1),'YData',p(2),'ZData',p(3),'UData',s*R(1,k),'VData',s*R(2,k),'WData',s*R(3,k)); end, end
function s=onOff(tf), if tf, s='on'; else, s='off'; end, end
function s=vstr(v), s=sprintf('[%.3f %.3f %.3f]',v(1),v(2),v(3)); end
function d=jointDistance(q,q0), dq=wrapToPiLocal(q-q0); dq(4)=q(4)-q0(4); d=norm(dq); end
function a=uniqueTol(a,tol), if isempty(a), return; end, a=sort(a(:).'); keep=[true,abs(diff(a))>tol]; a=a(keep); end
function tf=inLimit(q,lim), tf=q>=lim(1)-1e-10 && q<=lim(2)+1e-10; end
function q=normalizeToLimit(qraw,lim), c=qraw+2*pi*(-2:2); v=c(c>=lim(1)-1e-10 & c<=lim(2)+1e-10); if isempty(v), q=NaN; else, [~,i]=min(abs(v-qraw)); q=v(i); end, end
function x=wrapToPiLocal(x), x=mod(x+pi,2*pi)-pi; end
function T=Rx(q), c=cos(q);s=sin(q);T=[1 0 0 0;0 c -s 0;0 s c 0;0 0 0 1];end
function T=Ry(q), c=cos(q);s=sin(q);T=[c 0 s 0;0 1 0 0;-s 0 c 0;0 0 0 1];end
function T=Rz(q), c=cos(q);s=sin(q);T=[c -s 0 0;s c 0 0;0 0 1 0;0 0 0 1];end
function T=Tx(x), T=eye(4);T(1,4)=x;end
function T=Tr(x,y,z), T=eye(4);T(1:3,4)=[x;y;z];end
