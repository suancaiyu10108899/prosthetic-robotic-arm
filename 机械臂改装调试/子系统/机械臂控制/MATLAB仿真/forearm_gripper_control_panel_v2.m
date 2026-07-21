function forearm_gripper_control_panel_v2
% FOREARM_GRIPPER_CONTROL_PANEL_V2
% 3-DOF 前臂腕部 + 1-DOF 平行四边形夹爪交互仿真。
% MATLAB R2024b；可与 Peter Corke Robotics Toolbox 10.4 共存。
%
% 功能：
%   1) 4 个主动变量实时控制：q1、q2、q3、g
%   2) STL、骨架、关节轴、坐标系、TCP、轨迹显示
%   3) 正运动学、中间关节点、6x4 几何雅可比和奇异值
%   4) PDF 理论限位内的位置工作空间与当前 g 切片
%   5) 解析雅可比中心差分自检
%
% 坐标约定：世界原点在袖筒与第一旋转基座连接处，袖筒固定。
% 长度单位 mm；角度在界面中为 deg，内部为 rad。

%% 1. 参数
model.stlDir = 'D:\假肢机械臂\机械臂改装调试\原始资料\STL模型\stl_files';
assert(isfolder(model.stlDir), '找不到 STL 文件夹：%s', model.stlDir);

model.L12 = 50;
model.L23 = 30;
model.grip.rootX = 54;
model.grip.rootY = 6;
model.grip.linkX = 53;
model.grip.linkY = 2;
model.grip.contactX = 40;

% PDF 理论限位 [min,max]，deg
model.qlimDeg = [-180 180; -90 15; -180 180; 0 90];
model.names = {'q1 前臂旋转','q2 腕部俯仰','q3 腕部滚转','g 夹爪开合'};
model.shortNames = {'q1','q2','q3','g'};

% 实物观察修正后的网格/几何运动方向：g 增大时夹爪打开
% qA=+g, qB=-g, qTipA=-g, qTipB=+g
model.grip.coupling = [1;-1;-1;1];

model.workspace.fastN = [37,22,13];       % q1,q2,g 快速点云采样数
model.workspace.sliceN = [73,43];         % 固定 g 切片采样数
model.maxMeshFaces = 25000;
model.frameScale = 24;
model.axisLength = [90,90,90,55,55,45,45];

%% 2. 读取网格（只读一次）
files = {'socket.stl','wrsit_body.stl','wrist_roll.stl','gripper_body.stl', ...
         'finger_body_a.stl','finger_body_b.stl','fingertip_a.stl','fingertip_b.stl'};
keys = {'socket','wristBody','wristRoll','gripper','fingerA','fingerB','tipA','tipB'};
colors = [0.35 0.35 0.38; 0.20 0.48 0.80; 0.25 0.68 0.72; 0.85 0.55 0.18; ...
          0.82 0.25 0.22; 0.82 0.25 0.22; 0.95 0.72 0.25; 0.95 0.72 0.25];
mesh = struct;
for i=1:numel(files)
    fileName = fullfile(model.stlDir,files{i});
    assert(isfile(fileName),'缺少 STL：%s',fileName);
    TR = stlread(fileName);
    F = TR.ConnectivityList; V = TR.Points;
    if size(F,1)>model.maxMeshFaces
        [F,V] = reducepatch(F,V,model.maxMeshFaces);
    end
    mesh.(keys{i}) = struct('F',F,'V',V,'color',colors(i,:));
end

%% 3. UI 与状态
state.qDeg = [0;0;0;0];
state.track = zeros(0,3);
state.workspaceMode = '隐藏';
state.workspacePoints = zeros(0,3);

fig = uifigure('Name','前臂-腕部-平行夹爪运动学控制台 V2', ...
    'Position',[40 40 1520 900],'Color',[0.96 0.97 0.98]);
main = uigridlayout(fig,[1 2]);
main.ColumnWidth = {1000,'1x'};
main.Padding = [8 8 8 8]; main.ColumnSpacing = 8;

ax = uiaxes(main); ax.Layout.Row=1; ax.Layout.Column=1;
hold(ax,'on'); grid(ax,'on'); axis(ax,'equal'); axis(ax,'vis3d');
xlabel(ax,'X / mm'); ylabel(ax,'Y / mm'); zlabel(ax,'Z / mm');
title(ax,'前臂-腕部-夹爪交互运动学'); view(ax,35,25);
ax.XLim=[-240 280]; ax.YLim=[-260 260]; ax.ZLim=[-260 260];

right = uigridlayout(main,[3 1]); right.Layout.Column=2;
right.RowHeight={285,220,'1x'}; right.RowSpacing=6; right.Padding=[0 0 0 0];

% 关节控制区
pControl = uipanel(right,'Title','关节控制（界面 deg / 内部 rad）','FontWeight','bold');
gControl = uigridlayout(pControl,[6 4]);
gControl.RowHeight={38,38,38,38,38,'1x'};
gControl.ColumnWidth={115,'1x',80,68};
slider = gobjects(4,1); field = gobjects(4,1);
for i=1:4
    uilabel(gControl,'Text',model.names{i});
    slider(i)=uislider(gControl,'Limits',model.qlimDeg(i,:), ...
        'Value',state.qDeg(i),'MajorTicks',linspace(model.qlimDeg(i,1),model.qlimDeg(i,2),5));
    field(i)=uieditfield(gControl,'numeric','Limits',model.qlimDeg(i,:), ...
        'Value',state.qDeg(i),'ValueDisplayFormat','%.2f');
    uilabel(gControl,'Text',sprintf('[%g,%g]',model.qlimDeg(i,:)),'HorizontalAlignment','center');
    slider(i).ValueChangingFcn=@(src,event)sliderMoving(i,event.Value);
    slider(i).ValueChangedFcn=@(src,event)sliderFinished(i,event.Value);
    field(i).ValueChangedFcn=@(src,event)fieldChanged(i,event.Value);
end
btnZero=uibutton(gControl,'Text','全部回零','ButtonPushedFcn',@(~,~)setPose([0;0;0;0]));
btnRandom=uibutton(gControl,'Text','随机合法姿态','ButtonPushedFcn',@(~,~)setRandomPose());
btnClear=uibutton(gControl,'Text','清除 TCP 轨迹','ButtonPushedFcn',@(~,~)clearTrack());
btnCheck=uibutton(gControl,'Text','验证雅可比','ButtonPushedFcn',@(~,~)checkJacobian());
btnZero.Layout.Column=1; btnRandom.Layout.Column=2; btnClear.Layout.Column=3; btnCheck.Layout.Column=4;

% 显示与工作空间区
pDisplay=uipanel(right,'Title','显示与工作空间','FontWeight','bold');
gDisplay=uigridlayout(pDisplay,[5 4]);
gDisplay.RowHeight={32,32,32,32,'1x'};
cbSTL=uicheckbox(gDisplay,'Text','STL','Value',true,'ValueChangedFcn',@(~,~)applyVisibility());
cbSkeleton=uicheckbox(gDisplay,'Text','骨架','Value',true,'ValueChangedFcn',@(~,~)applyVisibility());
cbAxis=uicheckbox(gDisplay,'Text','关节轴','Value',true,'ValueChangedFcn',@(~,~)applyVisibility());
cbFrame=uicheckbox(gDisplay,'Text','坐标系','Value',true,'ValueChangedFcn',@(~,~)applyVisibility());
cbTCP=uicheckbox(gDisplay,'Text','TCP/接触点','Value',true,'ValueChangedFcn',@(~,~)applyVisibility());
cbTrack=uicheckbox(gDisplay,'Text','TCP轨迹','Value',true,'ValueChangedFcn',@(~,~)applyVisibility());
cbAutoTrack=uicheckbox(gDisplay,'Text','记录轨迹','Value',true);
cbTransparent=uicheckbox(gDisplay,'Text','半透明STL','Value',false,'ValueChangedFcn',@(~,~)applyVisibility());
uilabel(gDisplay,'Text','工作空间模式');
ddWorkspace=uidropdown(gDisplay,'Items',{'隐藏','全部理论范围','当前 g 切片'}, ...
    'Value','隐藏','ValueChangedFcn',@(~,~)workspaceChanged());
ddWorkspace.Layout.Column=[2 3];
btnCompute=uibutton(gDisplay,'Text','计算/刷新','ButtonPushedFcn',@(~,~)computeWorkspace());
uilabel(gDisplay,'Text','点云说明：q3 不改变 TCP 位置');
uilabel(gDisplay,'Text','全部范围采样 q1,q2,g；切片固定当前 g');
cbSTL.Layout.Row=1; cbSkeleton.Layout.Row=1; cbAxis.Layout.Row=1; cbFrame.Layout.Row=1;
cbTCP.Layout.Row=2; cbTrack.Layout.Row=2; cbAutoTrack.Layout.Row=2; cbTransparent.Layout.Row=2;

% 数据标签页
tabs=uitabgroup(right);
tabState=uitab(tabs,'Title','状态');
tabJ=uitab(tabs,'Title','雅可比');
tabT=uitab(tabs,'Title','变换/点');
stateText=uitextarea(tabState,'Editable','off','FontName','Consolas','FontSize',12,'Position',[5 5 475 310]);
jText=uitextarea(tabJ,'Editable','off','FontName','Consolas','FontSize',11,'Position',[5 5 475 310]);
tText=uitextarea(tabT,'Editable','off','FontName','Consolas','FontSize',11,'Position',[5 5 475 310]);

%% 4. 创建图元
% 每个 STL 使用 hgtransform，更新时只改 Matrix
hT=struct; hPatch=struct;
for i=1:numel(keys)
    hT.(keys{i})=hgtransform(ax);
    M=mesh.(keys{i});
    hPatch.(keys{i})=patch(ax,'Faces',M.F,'Vertices',M.V,'Parent',hT.(keys{i}), ...
        'FaceColor',M.color,'EdgeColor','none','AmbientStrength',0.35, ...
        'DiffuseStrength',0.75,'SpecularStrength',0.12);
end

hSkeleton(1)=plot3(ax,nan,nan,nan,'k.-','LineWidth',2,'MarkerSize',18);
hSkeleton(2)=plot3(ax,nan,nan,nan,'m.-','LineWidth',2,'MarkerSize',16);
hSkeleton(3)=plot3(ax,nan,nan,nan,'m.-','LineWidth',2,'MarkerSize',16);

hAxes=gobjects(7,1); axisColors={[.8 .1 .1],[.1 .65 .1],[.8 .1 .1],[.1 .25 .9],[.1 .25 .9],[.15 .45 1],[.15 .45 1]};
for i=1:7, hAxes(i)=plot3(ax,nan,nan,nan,'--','Color',axisColors{i},'LineWidth',1.8); end

% 4 个坐标系 x 3 根箭头
hFrames=gobjects(4,3);
for i=1:4
    hFrames(i,1)=quiver3(ax,0,0,0,0,0,0,0,'r','LineWidth',1.6);
    hFrames(i,2)=quiver3(ax,0,0,0,0,0,0,0,'g','LineWidth',1.6);
    hFrames(i,3)=quiver3(ax,0,0,0,0,0,0,0,'b','LineWidth',1.6);
end
hTCP=plot3(ax,nan,nan,nan,'kp','MarkerFaceColor','y','MarkerSize',13);
hContacts=plot3(ax,nan,nan,nan,'co','MarkerFaceColor','c','MarkerSize',8);
hTrack=plot3(ax,nan,nan,nan,'Color',[0.55 0 0.75],'LineWidth',1.7);
hWorkspace=scatter3(ax,nan,nan,nan,5,[0.15 .55 .95],'filled','MarkerFaceAlpha',0.18);
camlight(ax,'headlight'); lighting(ax,'gouraud');

updateAll(false);

%% ===================== UI 回调 =====================
    function sliderMoving(i,val)
        state.qDeg(i)=val; field(i).Value=val; updateAll(true);
    end
    function sliderFinished(i,val)
        state.qDeg(i)=val; field(i).Value=val; updateAll(true);
    end
    function fieldChanged(i,val)
        state.qDeg(i)=val; slider(i).Value=val; updateAll(true);
    end
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
    function workspaceChanged()
        state.workspaceMode=ddWorkspace.Value;
        if strcmp(state.workspaceMode,'隐藏')
            state.workspacePoints=zeros(0,3); applyVisibility();
        else
            computeWorkspace();
        end
    end
    function computeWorkspace()
        state.workspaceMode=ddWorkspace.Value;
        switch state.workspaceMode
            case '隐藏'
                state.workspacePoints=zeros(0,3);
            case '全部理论范围'
                state.workspacePoints=sampleWorkspace(model,model.workspace.fastN,[]);
            case '当前 g 切片'
                state.workspacePoints=sampleWorkspace(model,model.workspace.sliceN,deg2rad(state.qDeg(4)));
        end
        if isempty(state.workspacePoints)
            set(hWorkspace,'XData',nan,'YData',nan,'ZData',nan);
        else
            set(hWorkspace,'XData',state.workspacePoints(:,1),'YData',state.workspacePoints(:,2),'ZData',state.workspacePoints(:,3));
        end
        applyVisibility();
    end
    function checkJacobian()
        q=deg2rad(state.qDeg);
        [Ja,~,~]=modelKinematics(q,model);
        Jn=numericalJacobian(@(qq)modelKinematicsOnly(qq,model),q);
        D=Ja-Jn;
        uialert(fig,sprintf('Frobenius 误差 = %.3e\n最大元素误差 = %.3e',norm(D,'fro'),max(abs(D),[],'all')), ...
            '雅可比中心差分验证');
    end
    function updateAll(recordTrack)
        q=deg2rad(state.qDeg);
        [J,K,Ttcp]=modelKinematics(q,model);

        % STL 变换
        hT.socket.Matrix=eye(4);
        hT.wristBody.Matrix=K.T_wristBody;
        hT.wristRoll.Matrix=K.T_wristRoll;
        hT.gripper.Matrix=K.T_gripper;
        hT.fingerA.Matrix=K.T_fingerA;
        hT.fingerB.Matrix=K.T_fingerB;
        hT.tipA.Matrix=K.T_tipA;
        hT.tipB.Matrix=K.T_tipB;

        set(hSkeleton(1),'XData',[K.p1(1),K.p2(1),K.p3(1)],'YData',[K.p1(2),K.p2(2),K.p3(2)],'ZData',[K.p1(3),K.p2(3),K.p3(3)]);
        set(hSkeleton(2),'XData',[K.p3(1),K.pFingerA(1),K.pTipA(1),K.pContactA(1)],'YData',[K.p3(2),K.pFingerA(2),K.pTipA(2),K.pContactA(2)],'ZData',[K.p3(3),K.pFingerA(3),K.pTipA(3),K.pContactA(3)]);
        set(hSkeleton(3),'XData',[K.p3(1),K.pFingerB(1),K.pTipB(1),K.pContactB(1)],'YData',[K.p3(2),K.pFingerB(2),K.pTipB(2),K.pContactB(2)],'ZData',[K.p3(3),K.pFingerB(3),K.pTipB(3),K.pContactB(3)]);

        pts={K.p1,K.p2,K.p3,K.pFingerA,K.pFingerB,K.pTipA,K.pTipB};
        dirs={K.a1,K.a2,K.a3,K.aGripZ,K.aGripZ,K.aFingerAZ,K.aFingerBZ};
        for k=1:7, setAxisLine(hAxes(k),pts{k},dirs{k},model.axisLength(k)); end
        frames={eye(4),K.T_pitch,K.T_gripper,Ttcp};
        for k=1:4, setFrameGraphics(hFrames(k,:),frames{k},model.frameScale); end

        p=Ttcp(1:3,4);
        set(hTCP,'XData',p(1),'YData',p(2),'ZData',p(3));
        set(hContacts,'XData',[K.pContactA(1),K.pContactB(1)],'YData',[K.pContactA(2),K.pContactB(2)],'ZData',[K.pContactA(3),K.pContactB(3)]);
        if recordTrack && cbAutoTrack.Value
            state.track(end+1,:)=p.';
            if size(state.track,1)>3000, state.track=state.track(end-2999:end,:); end
        end
        if isempty(state.track), set(hTrack,'XData',nan,'YData',nan,'ZData',nan);
        else, set(hTrack,'XData',state.track(:,1),'YData',state.track(:,2),'ZData',state.track(:,3)); end

        % 数据输出
        sv=svd(J); rankJ=rank(J,1e-8); rankV=rank(J(1:3,:),1e-8);
        cJ=cond(J); if ~isfinite(cJ), cJ=Inf; end
        qActual=rad2deg(K.qGrip);
        stateText.Value=splitlines(sprintf([ ...
            '主动变量 [deg]\n q1=%9.3f  q2=%9.3f\n q3=%9.3f  g =%9.3f\n\n' ...
            '受约束夹爪角 [deg]\n A=%9.3f  B=%9.3f\n TipA=%6.3f  TipB=%6.3f\n\n' ...
            'TCP [mm]\n x=%10.4f\n y=%10.4f\n z=%10.4f\n\n' ...
            '夹持宽度 = %.4f mm\nTCP轴向半径(相对Roll) = %.4f mm\n'], ...
            state.qDeg(1),state.qDeg(2),state.qDeg(3),state.qDeg(4),qActual(1),qActual(2),qActual(3),qActual(4),p,K.gripWidth,K.tcpRadius));
        jText.Value=splitlines(sprintf([ ...
            'J0 = [Jv; Jw]，6x4\n%s\n\n' ...
            'rank(J)=%d, rank(Jv)=%d\ncond(J)=%.5g\n奇异值：\n%s\n\n' ...
            '列顺序：[q1 q2 q3 g]\n线速度：mm/s；角速度：rad/s'], ...
            mat2str(J,5),rankJ,rankV,cJ,mat2str(sv,5)));
        tText.Value=splitlines(sprintf([ ...
            'T0_TCP =\n%s\n\n关键点 [mm]\nPitch %s\nRoll  %s\nFingerA %s\nFingerB %s\nTipA %s\nTipB %s\nContactA %s\nContactB %s'], ...
            mat2str(Ttcp,5),vstr(K.p2),vstr(K.p3),vstr(K.pFingerA),vstr(K.pFingerB),vstr(K.pTipA),vstr(K.pTipB),vstr(K.pContactA),vstr(K.pContactB)));
        applyVisibility(); drawnow limitrate;
    end
    function applyVisibility()
        set(struct2array(hPatch),'Visible',onOff(cbSTL.Value));
        alphaVal=1.0; if cbTransparent.Value, alphaVal=0.38; end
        set(struct2array(hPatch),'FaceAlpha',alphaVal);
        set(hSkeleton,'Visible',onOff(cbSkeleton.Value));
        set(hAxes,'Visible',onOff(cbAxis.Value));
        set(hFrames(:),'Visible',onOff(cbFrame.Value));
        set([hTCP,hContacts],'Visible',onOff(cbTCP.Value));
        set(hTrack,'Visible',onOff(cbTrack.Value));
        showWs=~strcmp(state.workspaceMode,'隐藏') && ~isempty(state.workspacePoints);
        set(hWorkspace,'Visible',onOff(showWs));
    end
end

%% ===================== 运动学核心 =====================
function [J,K,Ttcp]=modelKinematics(q,m)
q1=q(1); q2=q(2); q3=q(3); g=q(4);
T01=Rx(q1);
T_pitch=T01*Tx(m.L12);
T02=T_pitch*Ry(q2);
T_roll=T02*Tx(m.L23);
T03=T_roll*Rx(q3);

qGrip=m.grip.coupling*g; % [qA;qB;qTipA;qTipB]
TA=T03*Tr(m.grip.rootX,m.grip.rootY,0)*Rz(qGrip(1));
TB=T03*Tr(m.grip.rootX,-m.grip.rootY,0)*Rz(qGrip(2));
TTA=TA*Tr(m.grip.linkX,m.grip.linkY,0)*Rz(qGrip(3));
TTB=TB*Tr(m.grip.linkX,-m.grip.linkY,0)*Rz(qGrip(4));

pCA=TTA(1:3,4)+TTA(1:3,1:3)*[m.grip.contactX;0;0];
pCB=TTB(1:3,4)+TTB(1:3,1:3)*[m.grip.contactX;0;0];
pTCP=0.5*(pCA+pCB);
% 理想平行四边形：TCP 姿态与 Gripper 坐标系一致
Ttcp=[T03(1:3,1:3),pTCP;0 0 0 1];

K.T_wristBody=T01; K.T_pitch=T_pitch; K.T_wristRoll=T02;
K.T_gripper=T03; K.T03=T03; K.T_fingerA=TA; K.T_fingerB=TB; K.T_tipA=TTA; K.T_tipB=TTB;
K.p1=[0;0;0]; K.p2=T_pitch(1:3,4); K.p3=T_roll(1:3,4);
K.pFingerA=TA(1:3,4); K.pFingerB=TB(1:3,4); K.pTipA=TTA(1:3,4); K.pTipB=TTB(1:3,4);
K.pContactA=pCA; K.pContactB=pCB; K.qGrip=qGrip;
K.a1=[1;0;0]; K.a2=T01(1:3,1:3)*[0;1;0]; K.a3=T02(1:3,1:3)*[1;0;0];
K.aGripZ=T03(1:3,1:3)*[0;0;1]; K.aFingerAZ=TA(1:3,1:3)*[0;0;1]; K.aFingerBZ=TB(1:3,1:3)*[0;0;1];
K.gripWidth=norm(pCA-pCB);
K.tcpRadius=norm(pTCP-K.p3);

p=pTCP;
Jv1=cross(K.a1,p-K.p1); Jv2=cross(K.a2,p-K.p2); Jv3=cross(K.a3,p-K.p3);
% 修正方向后 x_TCP^G = rootX + linkX*cos(g) - linkY*sin(g) + contactX
dx=-m.grip.linkX*sin(g)-m.grip.linkY*cos(g);
Jv4=T03(1:3,1:3)*[dx;0;0];
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
if isempty(fixedG), gv=linspace(m.qlimDeg(4,1),m.qlimDeg(4,2),N(3));
else, gv=rad2deg(fixedG); end
[Q1,Q2,G]=ndgrid(deg2rad(q1),deg2rad(q2),deg2rad(gv));
% TCP 位置解析式；q3 对位置无影响
L=m.L23+m.grip.rootX+m.grip.linkX.*cos(G)-m.grip.linkY.*sin(G)+m.grip.contactX;
X=m.L12+L.*cos(Q2);
Y=L.*sin(Q1).*sin(Q2);
Z=-L.*cos(Q1).*sin(Q2);
P=[X(:),Y(:),Z(:)];
end

%% ===================== 绘图辅助 =====================
function setAxisLine(h,p,a,L)
a=a/norm(a); p0=p-.5*L*a; p1=p+.5*L*a;
set(h,'XData',[p0(1),p1(1)],'YData',[p0(2),p1(2)],'ZData',[p0(3),p1(3)]);
end
function setFrameGraphics(h,T,s)
p=T(1:3,4); R=T(1:3,1:3);
for k=1:3, set(h(k),'XData',p(1),'YData',p(2),'ZData',p(3),'UData',s*R(1,k),'VData',s*R(2,k),'WData',s*R(3,k)); end
end
function s=onOff(tf), if tf, s='on'; else, s='off'; end, end
function s=vstr(v), s=sprintf('[%.3f %.3f %.3f]',v(1),v(2),v(3)); end

%% ===================== 基本齐次变换 =====================
function T=Rx(q), c=cos(q);s=sin(q);T=[1 0 0 0;0 c -s 0;0 s c 0;0 0 0 1];end
function T=Ry(q), c=cos(q);s=sin(q);T=[c 0 s 0;0 1 0 0;-s 0 c 0;0 0 0 1];end
function T=Rz(q), c=cos(q);s=sin(q);T=[c -s 0 0;s c 0 0;0 0 1 0;0 0 0 1];end
function T=Tx(x), T=eye(4);T(1,4)=x;end
function T=Tr(x,y,z), T=eye(4);T(1:3,4)=[x;y;z];end
