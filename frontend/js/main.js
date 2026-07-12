document.addEventListener('DOMContentLoaded', () => {
    let scene, camera, renderer, gearbox, hsShaft, lsShaft;
    let sunGear, gear1, gear2; 
    let vibrationChart = null;
    let isEnvelopeMode = false;
    let trendLineChart = null, faultTypePieChart = null, severityBarChart = null;
    let dashboardMetricChart = null, dashboardHealthGauge = null, vibrationFeatureChart = null;
    let latestStatus = null;
    let twinStructure = null;
    let twinComponents = {};
    let twinComponentState = {};
    let selectedTwinComponent = null;
    let selectedDetailUnit = 'WTG-001';
    let unitOptionsCache = Array.from({ length: 56 }, (_, idx) => ({ id: `WTG-${String(idx + 1).padStart(3, '0')}`, number: idx + 1 }));
    let windfarmViewMode = 'environment';
    let latestWindfarmData = null;
    let latestTurbineDetail = null;
    let dashboardSyncTimer = null;
    let turbineDetailTimer = null;
    let isTurbineDetailFetching = false;
    let detail3d = null;
    let systemNotifications = [];
    let faultCodeItems = [];
    let faultCodeTimer = null;
    let pendingDetailFocus = null;
    let notificationsRead = false;
    let notificationReadIds = new Set();
    let notificationSignature = '';
    let alarmThresholds = {
        temp_warning_threshold: 75,
        temp_threshold: 85,
        vibration_threshold: 4.5,
        vibration_critical_threshold: 7.1,
        oil_warning_threshold: 8,
        oil_quality_threshold: 10
    };
    let alarmThresholdsLoaded = false;
    const initialParams = new URLSearchParams(window.location.search);
    const requestedDetailUnit = initialParams.get('detail');
    const requestedInitialView = initialParams.get('view');
    const container = document.getElementById('three-container');
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();

    function initThree() {
        try {
            if (!container) return;
            if (renderer && scene && camera) {
                resizeDashboardTwin3D();
                return;
            }
            
            if (typeof THREE === 'undefined') {
                setTimeout(initThree, 500);
                return;
            }

        container.querySelectorAll('canvas').forEach(canvas => canvas.remove());
        
        scene = new THREE.Scene();
        camera = new THREE.PerspectiveCamera(75, container.clientWidth / container.clientHeight, 0.1, 1000);
        renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
        renderer.domElement.setAttribute('aria-label', '齿轮箱数字孪生热图');
        
        const width = container.clientWidth || 600;
        const height = container.clientHeight || 350;
        renderer.setSize(width, height);
        camera.aspect = width / height;
        camera.updateProjectionMatrix();
        
        container.appendChild(renderer.domElement);
        resizeDashboardTwin3D();

        const ambientLight = new THREE.AmbientLight(0x404040, 2);
        scene.add(ambientLight);
        const pointLight = new THREE.PointLight(0xffffff, 2);
        pointLight.position.set(10, 10, 10);
        scene.add(pointLight);

        const grid = new THREE.GridHelper(10, 20, 0x3b82f6, 0x1e293b);
        grid.position.y = -1.5;
        grid.material.opacity = 0.15;
        grid.material.transparent = true;
        scene.add(grid);

        const structure = new THREE.Group();

        const planetaryGeo = new THREE.CylinderGeometry(1.2, 1.2, 1.2, 32);
        const planetaryMat = new THREE.MeshPhongMaterial({ color: 0x334155, transparent: true, opacity: 0.2, wireframe: false });
        const planetaryStage = new THREE.Mesh(planetaryGeo, planetaryMat);
        planetaryStage.rotation.z = Math.PI / 2;
        planetaryStage.position.x = -1;
        structure.add(planetaryStage);

        const sunGeo = new THREE.CylinderGeometry(0.4, 0.4, 0.8, 16);
        const sunMat = new THREE.MeshPhongMaterial({ color: 0x3b82f6, emissive: 0x000000 });
        sunGear = new THREE.Mesh(sunGeo, sunMat);
        sunGear.rotation.z = Math.PI / 2;
        sunGear.position.x = -1;
        structure.add(sunGear);

        const parallelGeo = new THREE.BoxGeometry(2.5, 1.5, 1.5);
        const parallelMat = new THREE.MeshPhongMaterial({ color: 0x475569, transparent: true, opacity: 0.15 });
        const parallelStage = new THREE.Mesh(parallelGeo, parallelMat);
        parallelStage.position.x = 0.8;
        structure.add(parallelStage);

        const gear1Geo = new THREE.CylinderGeometry(0.6, 0.6, 0.3, 16);
        gear1 = new THREE.Mesh(gear1Geo, new THREE.MeshPhongMaterial({ color: 0x64748b, emissive: 0x000000 }));
        gear1.rotation.z = Math.PI / 2;
        gear1.position.set(0.5, 0, 0);
        structure.add(gear1);

        const gear2Geo = new THREE.CylinderGeometry(0.3, 0.3, 0.3, 16);
        gear2 = new THREE.Mesh(gear2Geo, new THREE.MeshPhongMaterial({ color: 0x94a3b8, emissive: 0x000000 }));
        gear2.rotation.z = Math.PI / 2;
        gear2.position.set(1.5, 0.4, 0);
        structure.add(gear2);


        const lsGeometry = new THREE.CylinderGeometry(0.5, 0.5, 1.0, 32);
        const lsMaterial = new THREE.MeshPhongMaterial({ color: 0x64748b });
        lsShaft = new THREE.Mesh(lsGeometry, lsMaterial);
        lsShaft.rotation.z = Math.PI / 2;
        lsShaft.position.x = -2.0;
        structure.add(lsShaft);

        const hsGeometry = new THREE.CylinderGeometry(0.15, 0.15, 1.2, 32);
        const hsMaterial = new THREE.MeshPhongMaterial({ color: 0x94a3b8 });
        hsShaft = new THREE.Mesh(hsGeometry, hsMaterial);
        hsShaft.rotation.z = Math.PI / 2;
        hsShaft.position.x = 2.4;
        hsShaft.position.y = 0.4; 
        structure.add(hsShaft);

        const fanGeo = new THREE.BoxGeometry(0.05, 0.8, 0.8);
        const fanMat = new THREE.MeshPhongMaterial({ color: 0xef4444 });
        const fan = new THREE.Mesh(fanGeo, fanMat);
        fan.position.set(0.5, 0.8, 0);
        structure.add(fan);

        scene.add(structure);
        gearbox = planetaryStage; 
        twinStructure = structure;
        twinComponents = {
            sun: sunGear,
            gear1,
            gear2,
            hs: hsShaft,
            ls: lsShaft,
            housing: planetaryStage
        };
        Object.entries(twinComponents).forEach(([key, mesh]) => {
            if (mesh) mesh.userData.twinKey = key;
        });

        camera.position.z = 6;
        camera.position.y = 1.5;
        camera.position.x = 1;
        
        function animate() {
            requestAnimationFrame(animate);
            if (structure) {
                const power = latestStatus ? (latestStatus.power || 1200) : 1200;
                const baseSpeed = power / 1500;
                
                structure.rotation.y += 0.001;
                if (lsShaft) lsShaft.rotation.x += 0.01 * baseSpeed;
                if (sunGear) sunGear.rotation.x += 0.01 * baseSpeed;
                if (gear1) gear1.rotation.x += 0.03 * baseSpeed;
                if (gear2) gear2.rotation.x += 0.1 * baseSpeed;
                if (hsShaft) hsShaft.rotation.x += 0.15 * baseSpeed;
                if (fan) fan.rotation.x += 0.08 * baseSpeed; 
            }
            renderer.render(scene, camera);
        }

        animate();

        window.addEventListener('resize', () => {
            resizeDashboardTwin3D();
        });

        container.addEventListener('click', (event) => {
            const rect = container.getBoundingClientRect();
            mouse.x = ((event.clientX - rect.left) / container.clientWidth) * 2 - 1;
            mouse.y = -((event.clientY - rect.top) / container.clientHeight) * 2 + 1;

            raycaster.setFromCamera(mouse, camera);
            const intersects = raycaster.intersectObjects(structure.children, true);

            const overlay = document.getElementById('comp-info-overlay');
            if (intersects.length > 0) {
                const object = intersects[0].object;
                const nameEl = document.getElementById('comp-name');
                const wearEl = document.getElementById('comp-wear');
                const tempEl = document.getElementById('comp-temp');
                const rulEl = document.getElementById('comp-rul');

                const key = object.userData.twinKey || (object === sunGear ? 'sun' : object === gear1 ? 'gear1' : object === gear2 ? 'gear2' : object === hsShaft ? 'hs' : 'housing');
                const state = twinComponentState[key] || {};
                selectedTwinComponent = key;
                let compName = state.name || "未知组件";
                let wear = `${state.wear ?? 0.5}%`;
                let tempRise = `+${state.tempRise ?? 1.2} K`;
                let rul = `${state.rul ?? 240}d`;

                nameEl.innerText = compName;
                wearEl.innerText = wear;
                tempEl.innerText = tempRise;
                rulEl.innerText = rul;
                
                wearEl.className = parseFloat(wear) > 3 ? 'status-tag danger' : (parseFloat(wear) > 1.5 ? 'status-tag warning' : 'status-tag success');

                overlay.style.display = 'block';
            } else {
                overlay.style.display = 'none';
            }
        });

        let lastHovered = null;
        container.addEventListener('mousemove', (event) => {
            const rect = container.getBoundingClientRect();
            mouse.x = ((event.clientX - rect.left) / container.clientWidth) * 2 - 1;
            mouse.y = -((event.clientY - rect.top) / container.clientHeight) * 2 + 1;

            raycaster.setFromCamera(mouse, camera);
            const hoverTargets = [sunGear, gear1, gear2, hsShaft, lsShaft].filter(Boolean);
            const intersects = raycaster.intersectObjects(hoverTargets, true);

            if (intersects.length > 0) {
                const object = intersects[0].object;
                if (lastHovered && lastHovered !== object) {
                    lastHovered.material.emissive.setHex(0x000000);
                }
                object.material.emissive.setHex(0x1e3a8a);
                container.style.cursor = 'pointer';
            } else {
                if (lastHovered) lastHovered.material.emissive.setHex(0x000000);
                lastHovered = null;
                container.style.cursor = 'grab';
            }
        });
        } catch (threeErr) {
            console.error("Three.js init failed:", threeErr);
            if (container) container.innerHTML = '<p style="color:var(--text-secondary); padding:20px;">3D 模型初始化失败。</p>';
        }
    }
    
    initThree();

    /*
    const savedUser = localStorage.getItem('currentUser');
    if (savedUser) {
        try {
            const user = JSON.parse(savedUser);
            document.querySelector('.username').innerText = (user.role === 'admin' ? '高级工程师 ' : '运维人员 ') + user.username;
            
            setTimeout(() => {
                applyAuthority(user.role);
                    document.getElementById('login-overlay').style.display = 'none';
                document.getElementById('main-app').style.display = 'flex';
                if (document.getElementById('settings').style.display === 'block') {
                    initSettingsView();
                }
            }, 10);
        } catch (e) {
            localStorage.removeItem('currentUser');
        }
    }
    */
    
    document.getElementById('login-overlay').style.display = 'flex';
    document.getElementById('main-app').style.display = 'none';

    const tabLogin = document.getElementById('tab-login');
    const tabRegister = document.getElementById('tab-register');
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');

    function updateModuleIndicator(targetId, sourceItem = null) {
        const item = sourceItem || document.querySelector(`.nav-item[data-target="${targetId}"]`);
        if (!item) return;
        const moduleName = item.dataset.module || '系统模块';
        const viewName = item.textContent.trim();
        const moduleDesc = item.dataset.moduleDesc || '';
        const app = document.getElementById('main-app');
        const moduleClass = moduleName.includes('智能诊断')
            ? 'module-diagnosis'
            : (moduleName.includes('系统配置') ? 'module-ops' : 'module-monitor');
        if (app) {
            app.classList.remove('module-monitor', 'module-diagnosis', 'module-ops');
            app.classList.add(moduleClass);
        }
        document.querySelectorAll('.nav-module-group').forEach(group => {
            group.classList.toggle('active', Boolean(group.contains(item)));
        });
        setText('current-module-name', moduleName);
        setText('current-view-name', viewName);
        setText('current-module-desc', moduleDesc);
    }

    function resizeDashboardTwin3D() {
        if (!container || !renderer || !camera) return;
        const width = Math.max(360, Math.floor(container.clientWidth || container.getBoundingClientRect().width || 600));
        const height = Math.max(320, Math.floor(container.clientHeight || container.getBoundingClientRect().height || 350));
        camera.aspect = width / height;
        camera.updateProjectionMatrix();
        renderer.setSize(width, height);
    }

    function showView(targetId) {
        const navItems = document.querySelectorAll('.nav-item');
        const sections = document.querySelectorAll('.view-section');
        navItems.forEach(item => item.classList.toggle('active', item.getAttribute('data-target') === targetId));
        sections.forEach(section => {
            section.style.display = section.id === targetId ? 'block' : 'none';
            section.classList.toggle('active', section.id === targetId);
        });
        updateModuleIndicator(targetId);
        if (targetId === 'windfarm') {
            fetchWindfarmOverview();
            stopTurbineDetailAutoRefresh();
        }
        if (targetId === 'dashboard') {
            fetchDashboardData();
            scheduleDashboardUnitSync();
        }
        if (targetId === 'ai-qa') {
            initQaUnitSelect();
            syncQaSelectedUnit();
        }
        if (targetId === 'turbine-detail') {
            fetchTurbineDetail(selectedDetailUnit);
            startTurbineDetailAutoRefresh();
        }
    }

    function showPostLoginDefault() {
        if (requestedDetailUnit) {
            selectedDetailUnit = requestedDetailUnit;
            initDetailUnitSelect();
            syncUnitSelectValue('detail-unit-select');
            showView('turbine-detail');
        } else if (requestedInitialView && document.getElementById(requestedInitialView)) {
            showView(requestedInitialView);
        } else {
            showView('windfarm');
        }
    }

    if (tabLogin && tabRegister) {
        tabLogin.addEventListener('click', () => {
            tabLogin.classList.add('active');
            tabRegister.classList.remove('active');
            tabLogin.style.color = 'white';
            tabRegister.style.color = 'rgba(255,255,255,0.4)';
            loginForm.style.display = 'block';
            registerForm.style.display = 'none';
        });
        tabRegister.addEventListener('click', () => {
            tabRegister.classList.add('active');
            tabLogin.classList.remove('active');
            tabRegister.style.color = 'white';
            tabLogin.style.color = 'rgba(255,255,255,0.4)';
            registerForm.style.display = 'block';
            loginForm.style.display = 'none';
        });
    }

    if (registerForm) {
        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const username = document.getElementById('reg-username').value;
            const password = document.getElementById('reg-password').value;
            const role = document.getElementById('reg-role').value;
            const submitBtn = registerForm.querySelector('button');

            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> 注册中...';

            try {
                const response = await fetch('/api/auth/register', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, password, role })
                });
                const data = await response.json();

                if (response.ok) {
                    alert('注册成功，正在为您登录...');
                    document.querySelector('.username').innerText = (role === 'admin' ? '高级工程师 ' : '运维人员 ') + username;
                    
                    localStorage.setItem('currentUser', JSON.stringify({ username, role }));

                    applyAuthority(role);
                    document.getElementById('login-overlay').style.display = 'none';
                    document.getElementById('main-app').style.display = 'flex';
                    showPostLoginDefault();
                } else {
                    alert(data.message || '注册失败');
                }
            } catch (error) {
                alert('注册失败，请检查后端连接');
            } finally {
                submitBtn.disabled = false;
                submitBtn.innerHTML = '注册并登录';
            }
        });
    }

    if (loginForm) {

        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const usernameInput = document.getElementById('username');
            const passwordInput = document.getElementById('password');
            const submitBtn = loginForm.querySelector('button');
            
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> 验证中...';

            try {
                const response = await fetch('/api/auth/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        username: usernameInput.value, 
                        password: passwordInput.value 
                    })
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    document.querySelector('.username').innerText = (data.user.role === 'admin' ? '高级工程师 ' : '运维人员 ') + data.user.username;
                    
                    localStorage.setItem('currentUser', JSON.stringify(data.user));
                    
                    applyAuthority(data.user.role);

                    document.getElementById('login-overlay').style.display = 'none';
                    document.getElementById('main-app').style.display = 'flex';
                    showPostLoginDefault();

                    
                    setTimeout(() => {
                        const charts = [vibrationChart, trendLineChart, faultTypePieChart, severityBarChart, dashboardMetricChart, dashboardHealthGauge, vibrationFeatureChart];
                        charts.forEach(chart => {
                            if (chart) chart.resize();
                        });
                    }, 300);
                } else {
                    alert(data.message || '登录失败');
                }
            } catch (error) {
                console.error('Login error:', error);
                alert('无法连接到认证服务器，请确保后端已启动');
            } finally {
                submitBtn.disabled = false;
                submitBtn.innerHTML = '登录';
            }
        });
    }


    const navItems = document.querySelectorAll('.nav-item');
    const sections = document.querySelectorAll('.view-section');

    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const targetId = item.getAttribute('data-target');
            pendingDetailFocus = item.dataset.detailFocus || null;
            
            navItems.forEach(n => n.classList.remove('active'));
            sections.forEach(s => s.style.display = 'none');
            
            item.classList.add('active');
            const targetSection = document.getElementById(targetId);
            if(targetSection) {
                targetSection.style.display = 'block';
                targetSection.classList.add('fade-in');
            }
            updateModuleIndicator(targetId, item);
            if (targetId !== 'turbine-detail') stopTurbineDetailAutoRefresh();
            if (targetId !== 'turbine-detail') stopFaultCodeAutoRefresh();

            if (targetId === 'diagnosis') {
                initDiagnosisUnitSelect();
            }
            if (targetId === 'ai-qa') {
                initQaUnitSelect();
                syncQaSelectedUnit();
            }
            if (targetId === 'dashboard' || targetId === 'data' || targetId === 'windfarm' || targetId === 'turbine-detail') {
                setTimeout(() => {
                    const charts = [vibrationChart, trendLineChart, faultTypePieChart, severityBarChart, dashboardMetricChart, dashboardHealthGauge, vibrationFeatureChart];
                    charts.forEach(chart => {
                        if (chart) chart.resize();
                    });
                    
                    if (targetId === 'dashboard') {
                        fetchAnalysisData(30);
                        fetchDashboardData();
                        scheduleDashboardUnitSync();
                    }
                    if (targetId === 'data') fetchFaultRecords();
                    if (targetId === 'windfarm') fetchWindfarmOverview();
                    if (targetId === 'turbine-detail') {
                        fetchTurbineDetail(selectedDetailUnit);
                        startTurbineDetailAutoRefresh();
                        fetchFaultCodeCatalog();
                        startFaultCodeAutoRefresh();
                        if (pendingDetailFocus === 'fault-hmi') {
                            setTimeout(() => focusDetailFaultHmi(), 400);
                        }
                    }
                }, 150);
            }
        });
    });

    function resizeDashboardCharts() {
        [dashboardMetricChart, dashboardHealthGauge, vibrationChart, vibrationFeatureChart, trendLineChart, faultTypePieChart, severityBarChart].forEach(chart => {
            if (chart) chart.resize();
        });
        resizeDashboardTwin3D();
        resizeDetailTurbine3D();
    }

    document.getElementById('dashboard-tabs')?.addEventListener('click', (event) => {
        const button = event.target.closest('button[data-dashboard-tab]');
        if (!button) return;
        const tab = button.dataset.dashboardTab;
        document.querySelectorAll('#dashboard-tabs button').forEach(item => {
            item.classList.toggle('active', item === button);
        });
        document.querySelectorAll('.dashboard-tab-panel').forEach(panel => {
            panel.classList.toggle('active', panel.dataset.dashboardPanel === tab);
        });
        if (tab === 'history') fetchAnalysisData(getCurrentAnalysisDays());
        if (tab === 'vibration') fetchDashboardData();
        if (tab === 'twin') {
            initThree();
            if (latestStatus) updateDigitalTwinHeat(latestStatus);
        }
        window.setTimeout(resizeDashboardCharts, 80);
    });

    function faultStateText(state) {
        if (state === 'critical') return '临界';
        if (state === 'warning') return '关注';
        if (state === 'normal') return '正常';
        return '无数据';
    }

    function initFaultCodeUnitSelect() {
        const select = document.getElementById('fault-code-unit-select');
        if (!select) return;
        if (!select.dataset.ready) {
            select.dataset.ready = 'true';
            select.innerHTML = buildUnitOptions();
            select.addEventListener('change', () => {
                setSelectedUnit(select.value);
                fetchFaultCodeCatalog();
            });
        }
        select.value = selectedDetailUnit;
    }

    function focusDetailFaultHmi() {
        const panel = document.getElementById('detail-fault-hmi-panel');
        if (!panel) return;
        panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
        panel.classList.add('focus-flash');
        window.setTimeout(() => panel.classList.remove('focus-flash'), 1200);
    }

    function setFaultCodeLevel(level = 'all') {
        const select = document.getElementById('fault-code-severity');
        if (select) select.value = level;
        document.querySelectorAll('[data-fault-level]').forEach(item => {
            item.classList.toggle('active', (item.dataset.faultLevel || 'all') === level);
        });
        applyFaultCodeFilters();
    }

    function scrollDetailArea(selector, block = 'start') {
        const target = document.querySelector(selector);
        target?.scrollIntoView({ behavior: 'smooth', block });
    }

    async function fetchFaultCodeCatalog() {
        initFaultCodeUnitSelect();
        const grid = document.getElementById('fault-code-grid');
        if (grid && !faultCodeItems.length) {
            grid.innerHTML = '<div class="fault-code-empty glass-panel">正在加载齿轮箱故障代码库...</div>';
        }
        try {
            const response = await fetch(`/api/data/fault-codes?unit_id=${encodeURIComponent(selectedDetailUnit)}&t=${Date.now()}`);
            if (!response.ok) throw new Error('fault code fetch failed');
            const data = await response.json();
            faultCodeItems = data.items || [];
            setText('fault-code-total', data.summary?.total ?? '--');
            setText('fault-code-critical', data.summary?.critical ?? '--');
            setText('fault-code-warning', data.summary?.warning ?? '--');
            setText('fault-code-sync', data.timestamp || '--');
            setText('fault-hmi-unit', data.unit_id || selectedDetailUnit);
            renderFaultCodeCategories();
            applyFaultCodeFilters();
        } catch (error) {
            if (grid) grid.innerHTML = '<div class="fault-code-empty glass-panel danger">故障代码库加载失败，请检查后端服务。</div>';
        }
    }

    function renderFaultCodeCategories() {
        const select = document.getElementById('fault-code-category');
        if (!select) return;
        const current = select.value || 'all';
        const categories = [...new Set(faultCodeItems.map(item => item.category).filter(Boolean))];
        select.innerHTML = '<option value="all">全部类别</option>' + categories.map(category => `<option value="${escapeHtml(category)}">${escapeHtml(category)}</option>`).join('');
        select.value = categories.includes(current) ? current : 'all';
    }

    function applyFaultCodeFilters() {
        const term = (document.getElementById('fault-code-search')?.value || '').trim().toLowerCase();
        const category = document.getElementById('fault-code-category')?.value || 'all';
        const severity = document.getElementById('fault-code-severity')?.value || 'all';
        const state = document.getElementById('fault-code-state')?.value || 'all';
        const filtered = faultCodeItems.filter(item => {
            const text = `${item.code} ${item.raw_code} ${item.source_code} ${item.severity_level} ${item.name} ${item.category} ${item.advice} ${item.source}`.toLowerCase();
            return (!term || text.includes(term))
                && (category === 'all' || item.category === category)
                && (severity === 'all' || String(item.severity_level) === severity)
                && (state === 'all' || item.state === state);
        });
        renderFaultCodeGrid(filtered);
    }

    function renderFaultCodeGrid(items) {
        const grid = document.getElementById('fault-code-grid');
        if (!grid) return;
        if (!items.length) {
            grid.innerHTML = '<div class="fault-code-empty">暂无匹配的齿轮箱故障类型。</div>';
            return;
        }
        const rows = [];
        const compact = Boolean(document.querySelector('.detail-fault-library'));
        if (compact) {
            grid.innerHTML = `
                <div class="detail-fault-list">
                    ${items.map(item => `
                        <div class="detail-fault-row ${escapeHtml(item.state)}">
                            <span class="fault-lamp ${escapeHtml(item.state)}" title="${escapeHtml(faultStateText(item.state))}"></span>
                            <b>${escapeHtml(item.code)}</b>
                            <div>
                                <strong>${escapeHtml(item.name)}</strong>
                                <small>${escapeHtml(item.category || '--')} · L${escapeHtml(item.severity_level || '--')} · ${escapeHtml(item.source || '--')}</small>
                            </div>
                            <em>${escapeHtml(faultStateText(item.state))}</em>
                        </div>
                    `).join('')}
                </div>
            `;
            return;
        }
        for (let i = 0; i < items.length; i += 2) rows.push([items[i], items[i + 1]]);
        const renderSide = (item) => {
            if (!item) return '<div class="fault-hmi-cell empty"></div>';
            return `
                <div class="fault-hmi-cell ${escapeHtml(item.state)}">
                    <span class="fault-lamp ${escapeHtml(item.state)}" title="${escapeHtml(faultStateText(item.state))}"></span>
                    <b>${escapeHtml(item.code)}</b>
                    <strong>${escapeHtml(item.name)}</strong>
                    <em>${escapeHtml(faultStateText(item.state))}</em>
                </div>
            `;
        };
        grid.innerHTML = `
            <div class="fault-hmi-list">
                ${rows.map(([left, right]) => `
                    <div class="fault-hmi-row">
                        ${renderSide(left)}
                        ${renderSide(right)}
                    </div>
                `).join('')}
            </div>
        `;
    }

    function startFaultCodeAutoRefresh() {
        stopFaultCodeAutoRefresh();
        faultCodeTimer = window.setInterval(() => {
            if (isViewVisible('turbine-detail')) fetchFaultCodeCatalog();
        }, 5000);
    }

    function stopFaultCodeAutoRefresh() {
        if (faultCodeTimer) {
            window.clearInterval(faultCodeTimer);
            faultCodeTimer = null;
        }
    }

    document.getElementById('fault-code-search')?.addEventListener('input', applyFaultCodeFilters);
    document.getElementById('fault-code-category')?.addEventListener('change', applyFaultCodeFilters);
    document.getElementById('fault-code-severity')?.addEventListener('change', applyFaultCodeFilters);
    document.getElementById('fault-code-state')?.addEventListener('change', applyFaultCodeFilters);
    document.querySelectorAll('[data-fault-level]').forEach(button => {
        button.addEventListener('click', () => {
            setFaultCodeLevel(button.dataset.faultLevel || 'all');
        });
    });
    document.getElementById('fault-code-refresh')?.addEventListener('click', () => {
        fetchFaultCodeCatalog();
        showActionToast(`已刷新 ${selectedDetailUnit} 齿轮箱故障代码状态`);
    });

    let allFaultRecords = [];
    let pendingClosureRecord = null;

    async function fetchFaultRecords() {
        const tableBody = document.querySelector('.data-table tbody');
            tableBody.innerHTML = '<tr><td colspan="6" style="text-align:center;">正在加载数据...</td></tr>';
        
        try {
            initFaultUnitFilter();
            const response = await fetch('/api/data/records');
            allFaultRecords = await response.json();
            applyFaultFilters();
        } catch (error) {
            tableBody.innerHTML = '<tr><td colspan="6" style="text-align:center; color:var(--danger);">加载失败，请检查后端连接</td></tr>';
        }
    }

    function initFaultUnitFilter() {
        const select = document.getElementById('fault-unit-filter');
        if (!select || select.dataset.ready) return;
        select.dataset.ready = 'true';
        select.innerHTML = `<option value="all">全部机组</option>${buildUnitOptions()}`;
        select.value = 'all';
    }

    function severityMeta(severity) {
        if (severity === '正常') return { className: 'success', icon: 'fa-circle-check', label: '正常' };
        if (severity === '警告') return { className: 'warning', icon: 'fa-circle-exclamation', label: '警告' };
        return { className: 'danger', icon: 'fa-triangle-exclamation', label: severity || '严重' };
    }

    function renderFaultTable(records) {
        const tableBody = document.querySelector('.data-table tbody');
        if (!tableBody) return;

        if (records.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="6" style="text-align:center;">暂无匹配的故障记录</td></tr>';
            return;
        }

        tableBody.innerHTML = '';
        records.forEach((r, index) => {
            const tr = document.createElement('tr');
            const severity = severityMeta(r.severity);
            const statusClass = r.status === 'processed' ? 'success' : 'warning';
            const statusIcon = r.status === 'processed' ? 'fa-circle-check' : 'fa-clock';
            const actionHtml = r.status === 'processed'
                ? '<span class="fault-done-text"><i class="fa-solid fa-check"></i> 已闭环</span>'
                : `<button class="fault-complete-btn" data-index="${index}"><i class="fa-solid fa-check"></i> 处理完成</button>`;
             
            tr.innerHTML = `
                <td><button class="unit-pill" data-unit="${escapeHtml(r.unit_id)}">${escapeHtml(r.unit_id)}</button></td>
                <td>${r.timestamp}</td>
                <td class="fault-type-cell">${escapeHtml(r.fault_type)}</td>
                <td><span class="severity-badge ${severity.className}"><i class="fa-solid ${severity.icon}"></i>${severity.label}</span></td>
                <td><span class="status-tag ${statusClass}"><i class="fa-solid ${statusIcon}"></i> ${r.status === 'processed' ? '已处理' : '待处理'}</span></td>
                <td>
                    <div class="fault-action-cell">
                        <a href="#" class="view-detail-link" data-index="${index}">查看详情</a>
                        ${actionHtml}
                    </div>
                </td>
            `;
            tableBody.appendChild(tr);
        });

        document.querySelectorAll('.unit-pill').forEach(button => {
            button.onclick = () => {
                const unitId = button.dataset.unit || selectedDetailUnit;
                setSelectedUnit(unitId);
                document.querySelector('[data-target="turbine-detail"]')?.click();
                fetchTurbineDetail(unitId);
                showActionToast(`已打开 ${unitId} 齿轮箱详情`);
            };
        });

        document.querySelectorAll('.view-detail-link').forEach(link => {
            link.onclick = (e) => {
                e.preventDefault();
                const idx = e.target.getAttribute('data-index');
                showFaultDetails(records[idx]);
            };
        });

        tableBody.querySelectorAll('.fault-complete-btn').forEach(button => {
            button.onclick = () => {
                const idx = button.getAttribute('data-index');
                openFaultClosureModal(records[idx]);
            };
        });
    }

    function openFaultClosureModal(record) {
        if (!record || record.status === 'processed') return;
        pendingClosureRecord = record;
        const modal = document.getElementById('closure-modal');
        const summary = document.getElementById('closure-record-summary');
        const owner = document.getElementById('closure-owner');
        const currentUser = JSON.parse(localStorage.getItem('currentUser') || '{}');
        if (summary) summary.textContent = `${record.unit_id} · ${record.timestamp} · ${record.fault_type} · ${record.severity}`;
        if (owner) owner.value = currentUser.username || 'operator01';
        if (modal) modal.style.display = 'flex';
    }

    function closeFaultClosureModal() {
        const modal = document.getElementById('closure-modal');
        if (modal) modal.style.display = 'none';
        pendingClosureRecord = null;
        document.getElementById('closure-form')?.reset();
    }

    function faultRecordKey(record) {
        if (!record) return '';
        if (record.id !== undefined && record.id !== null && record.id !== '') return `id:${record.id}`;
        return [
            record.unit_id || '',
            record.timestamp || '',
            record.fault_type || '',
            record.severity || ''
        ].join('|');
    }

    function isPersistedRecordId(id) {
        return /^\d+$/.test(String(id ?? ''));
    }

    function applyCompletedFaultRecord(record, serverRecord = null, closure = null) {
        const key = faultRecordKey(record);
        allFaultRecords = allFaultRecords.map(item => {
            if (faultRecordKey(item) !== key) return item;
            return {
                ...item,
                ...(serverRecord || {}),
                status: 'processed',
                work_order_action: closure?.action || '已处理',
                closure
            };
        });
        applyFaultFilters();
    }

    async function completeFaultRecord(record, sourceButton = null, closure = null) {
        if (!record || record.status === 'processed') return;

        if (sourceButton) sourceButton.disabled = true;

        try {
            let serverRecord = null;
            if (closure) {
                const closureResponse = await fetch('/api/data/records/complete', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        record_ref: String(record.id ?? faultRecordKey(record)),
                        unit_id: record.unit_id,
                        fault_type: record.fault_type,
                        ...closure
                    })
                });
                if (!closureResponse.ok) throw new Error('closure save failed');
                const closureResult = await closureResponse.json();
                closure = closureResult.closure || closure;
            }
            if (isPersistedRecordId(record.id)) {
                const response = await fetch(`/api/data/records/${encodeURIComponent(record.id)}/complete`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                if (!response.ok) throw new Error('complete failed');
                serverRecord = await response.json();
            }
            applyCompletedFaultRecord(record, serverRecord, closure);
            if (detailsModal) detailsModal.style.display = 'none';
            closeFaultClosureModal();
            showActionToast(`${record.unit_id} 故障记录已处理完成`);
        } catch (error) {
            console.error('Failed to complete fault record:', error);
            if (sourceButton) sourceButton.disabled = false;
            showActionToast('处理完成失败，请检查后端连接后重试', 'danger');
            applyFaultFilters();
        }
    }

    function updateFaultSummary(records) {
        setText('fault-total-count', records.length);
        setText('fault-critical-count', records.filter(r => r.severity === '严重').length);
        setText('fault-pending-count', records.filter(r => r.status !== 'processed').length);
        setText('fault-current-unit-count', records.filter(r => r.unit_id === selectedDetailUnit).length);
    }

    function applyFaultFilters(forceCurrentUnit = false) {
        const term = (document.getElementById('fault-search-input')?.value || '').toLowerCase();
        const unit = document.getElementById('fault-unit-filter')?.value || 'all';
        const severity = document.getElementById('fault-severity-filter')?.value || 'all';
        const status = document.getElementById('fault-status-filter')?.value || 'all';
        const filtered = allFaultRecords.filter(r => {
            const matchTerm = !term || r.unit_id.toLowerCase().includes(term) || r.fault_type.toLowerCase().includes(term) || r.severity.toLowerCase().includes(term);
            const matchUnitFilter = unit === 'all' || r.unit_id === unit;
            const matchSeverity = severity === 'all' || r.severity === severity;
            const matchStatus = status === 'all' || r.status === status;
            const matchUnit = !forceCurrentUnit || r.unit_id === selectedDetailUnit;
            return matchTerm && matchUnitFilter && matchSeverity && matchStatus && matchUnit;
        });
        updateFaultSummary(filtered);
        renderFaultTable(filtered);
    }

    function normalizeAlarmSearchKey(alarmKey = '') {
        const text = String(alarmKey).trim();
        if (!text) return '';
        if (/VIB|振动/i.test(text)) return '振动';
        if (/TEMP|油温|温度/i.test(text)) return '油温';
        if (/NAS|油液|润滑/i.test(text)) return '油液';
        if (/SCADA|停机|故障/i.test(text)) return '';
        return text.replace(/^FAULT[-_]?/i, '').slice(0, 12);
    }

    function openFaultDataForAlarm(unitId, alarmKey = '') {
        selectedDetailUnit = unitId || selectedDetailUnit;
        document.querySelector('[data-target="data"]')?.click();
        initFaultUnitFilter();
        const unitFilter = document.getElementById('fault-unit-filter');
        const statusFilter = document.getElementById('fault-status-filter');
        const searchInput = document.getElementById('fault-search-input');
        if (unitFilter) unitFilter.value = selectedDetailUnit;
        if (statusFilter) statusFilter.value = 'pending';
        if (searchInput) searchInput.value = normalizeAlarmSearchKey(alarmKey);
        if (allFaultRecords.length) {
            applyFaultFilters();
        } else {
            fetchFaultRecords();
        }
        showActionToast(`已筛选 ${selectedDetailUnit} 待处理故障记录`);
    }

    const faultSearchInput = document.getElementById('fault-search-input');
    if (faultSearchInput) {
        faultSearchInput.addEventListener('input', () => applyFaultFilters());
    }
    document.getElementById('fault-unit-filter')?.addEventListener('change', () => applyFaultFilters());
    document.getElementById('fault-severity-filter')?.addEventListener('change', () => applyFaultFilters());
    document.getElementById('fault-status-filter')?.addEventListener('change', () => applyFaultFilters());
    document.getElementById('fault-current-unit-btn')?.addEventListener('click', () => {
        const select = document.getElementById('fault-unit-filter');
        if (select) select.value = selectedDetailUnit;
        applyFaultFilters();
    });

    const exportCsvBtn = document.getElementById('export-fault-btn');
    if (exportCsvBtn) {
        exportCsvBtn.onclick = () => {
            window.location.href = '/api/data/records/export';
        };
    }

    const detailsModal = document.getElementById('details-modal');
    const detailsContent = document.getElementById('details-content');
    const closeDetailsBtn = document.getElementById('close-details-btn');
    const modalCloseBtn = document.getElementById('modal-close-btn');

    function showFaultDetails(record) {
        if (!detailsModal || !detailsContent) return;
        
        const severity = severityMeta(record.severity);

        detailsContent.innerHTML = `
            <div class="detail-item">
                <span class="detail-label">机组编号 / 发生时间</span>
                <div class="detail-value">${record.unit_id} <span style="color:var(--text-secondary); margin-left:10px;">${record.timestamp}</span></div>
            </div>
            <div class="detail-item">
                <span class="detail-label">故障类型 & 严重程度</span>
                <div class="detail-value">
                    ${record.fault_type} 
                    <span class="severity-badge ${severity.className}" style="margin-left:10px;"><i class="fa-solid ${severity.icon}"></i>${severity.label}</span>
                </div>
            </div>
            <div class="detail-item">
                <span class="detail-label">诊断概率 / 置信度</span>
                <div class="detail-value">${record.probability ? (record.probability * 100).toFixed(2) + '%' : '--'}</div>
            </div>
            <div class="detail-item">
                <span class="detail-label">状态评估建议</span>
                <div class="detail-value" style="background:rgba(255,255,255,0.03); padding:15px; border-radius:8px; border-left:3px solid var(--accent-color);">
                    ${record.advice}
                </div>
            </div>
            <div class="detail-item">
                <span class="detail-label">处理状态</span>
                <div class="detail-value">${record.status === 'processed' ? '<i class="fa-solid fa-check-circle" style="color:var(--success);"></i> 已完成维修闭环' : '<i class="fa-solid fa-clock" style="color:var(--warning);"></i> 正在等待现场排查'}</div>
            </div>
            ${record.closure ? `
            <div class="detail-item">
                <span class="detail-label">闭环记录</span>
                <div class="detail-value" style="background:rgba(16,185,129,0.08); padding:14px; border-radius:8px;">
                    ${escapeHtml(record.closure.owner || '--')} · ${escapeHtml(record.closure.action || '--')} · ${escapeHtml(record.closure.result || '--')}
                    <div style="color:var(--text-secondary); margin-top:6px;">${escapeHtml(record.closure.note || record.closure.closed_at || '')}</div>
                </div>
            </div>` : ''}
            ${record.status === 'processed' ? '' : `
            <div class="detail-item">
                <span class="detail-label">闭环操作</span>
                <div class="detail-value">
                    <button class="fault-complete-btn modal-complete-btn" id="modal-complete-fault-btn">
                        <i class="fa-solid fa-check"></i> 处理完成
                    </button>
                </div>
            </div>
            `}
        `;

        document.getElementById('modal-complete-fault-btn')?.addEventListener('click', () => {
            openFaultClosureModal(record);
        });
        
        detailsModal.style.display = 'flex';
    }

    if (closeDetailsBtn) closeDetailsBtn.onclick = () => detailsModal.style.display = 'none';
    if (modalCloseBtn) modalCloseBtn.onclick = () => detailsModal.style.display = 'none';
    document.getElementById('close-closure-btn')?.addEventListener('click', closeFaultClosureModal);
    document.getElementById('cancel-closure-btn')?.addEventListener('click', closeFaultClosureModal);
    document.getElementById('closure-form')?.addEventListener('submit', (event) => {
        event.preventDefault();
        if (!pendingClosureRecord) return;
        const closure = {
            owner: document.getElementById('closure-owner')?.value || '',
            action: document.getElementById('closure-action')?.value || '',
            result: document.getElementById('closure-result')?.value || '',
            note: document.getElementById('closure-note')?.value || '',
            closed_at: new Date().toLocaleString()
        };
        completeFaultRecord(pendingClosureRecord, event.submitter, closure);
    });
    
    const modalPrintBtn = document.getElementById('modal-print-btn');
    if (modalPrintBtn) {
        modalPrintBtn.onclick = () => {
            const content = detailsContent.innerHTML;
            const printWindow = window.open('', '_blank');
            printWindow.document.write(`
                <html>
                    <head>
                        <title>故障详情 - ${new Date().toLocaleString()}</title>
                        <style>
                            body { font-family: sans-serif; padding: 40px; color: #333; }
                            .detail-item { margin-bottom: 20px; border-bottom: 1px solid #eee; padding-bottom: 10px; }
                            .detail-label { color: #666; font-size: 0.9rem; }
                            .detail-value { font-weight: bold; margin-top: 5px; }
                            .badge { padding: 4px 8px; border-radius: 4px; background: #eee; font-size: 0.8rem; }
                        </style>
                    </head>
                    <body>
                        <h2>华锐 SL1500 齿轮箱故障详细记录</h2>
                        <hr>
                        ${content}
                    </body>
                </html>
            `);
            printWindow.document.close();
            printWindow.print();
        };
    }

    window.onclick = (event) => {
        if (event.target == detailsModal) detailsModal.style.display = 'none';
        if (event.target?.id === 'closure-modal') closeFaultClosureModal();
    };

    const sendBtn = document.getElementById('send-qa-btn');
    const qaInput = document.getElementById('qa-input');
    const chatHistory = document.getElementById('chat-history');
    const qaDeepThinking = document.getElementById('qa-deep-thinking');
    const qaPresetQuestions = {
        status: '结合当前机组油温、振动、油液、健康评分和 RUL，判断是否需要停机或生成工单。',
        temperature: '当前齿轮箱油温是否异常？请给出冷却、润滑和负荷侧排查步骤。',
        vibration: '当前振动 RMS 和特征趋势是否说明轴承或齿面风险？请给出诊断路径。',
        workorder: '如果当前风险继续恶化，应生成什么级别工单，责任人和复测项如何安排？',
        algorithm: '请解释 M-IALO-SVR 在油温残差预测和 RUL 评估中的作用，并说明如何验证结果。'
    };

    function escapeHtml(value) {
        return String(value ?? '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    function showActionToast(message, type = 'info') {
        let toast = document.getElementById('action-toast');
        if (!toast) {
            toast = document.createElement('div');
            toast.id = 'action-toast';
            document.body.appendChild(toast);
        }
        toast.className = `action-toast ${type}`;
        toast.textContent = message;
        window.clearTimeout(Number(toast.dataset.timer || 0));
        requestAnimationFrame(() => toast.classList.add('show'));
        toast.dataset.timer = String(window.setTimeout(() => {
            toast.classList.remove('show');
        }, 2200));
    }

    function notificationLevelText(level) {
        return {
            critical: '严重',
            warning: '告警',
            success: '恢复',
            info: '关注',
        }[level] || '提示';
    }

    function notificationIcon(level) {
        return {
            critical: 'fa-circle-exclamation',
            warning: 'fa-triangle-exclamation',
            success: 'fa-check-circle',
            info: 'fa-circle-info',
        }[level] || 'fa-circle-info';
    }

    function notificationId(item) {
        return btoa(unescape(encodeURIComponent(`${item.level}|${item.source}|${item.message}`))).replace(/=+$/, '');
    }

    function renderSystemNotifications() {
        const list = document.getElementById('notification-list');
        const badge = document.getElementById('notification-badge');
        const unreadEl = document.getElementById('notif-unread-count');
        const criticalEl = document.getElementById('notif-critical-count');
        const warningEl = document.getElementById('notif-warning-count');
        const syncEl = document.getElementById('notif-last-sync');
        if (!list) return;

        const unreadCount = systemNotifications.filter(item => !notificationReadIds.has(notificationId(item))).length;
        const criticalCount = systemNotifications.filter(item => item.level === 'critical').length;
        const warningCount = systemNotifications.filter(item => item.level === 'warning').length;
        if (badge) {
            badge.textContent = String(unreadCount);
            badge.style.display = unreadCount > 0 ? 'inline-block' : 'none';
        }
        setText('notif-unread-count', unreadCount);
        setText('notif-critical-count', criticalCount);
        setText('notif-warning-count', warningCount);
        if (syncEl) syncEl.textContent = `最近同步 ${new Date().toLocaleTimeString('zh-CN', { hour12: false })}`;

        if (!systemNotifications.length) {
            list.innerHTML = '<div class="notif-empty">暂无系统运行通知。</div>';
            return;
        }

        list.innerHTML = systemNotifications.map(item => {
            const id = notificationId(item);
            const isRead = notificationReadIds.has(id);
            return `
            <div class="notif-item ${escapeHtml(item.level)} ${isRead ? 'read' : 'unread'}" data-notif-id="${escapeHtml(id)}">
                <span class="notif-icon"><i class="fa-solid ${notificationIcon(item.level)}"></i></span>
                <div class="notif-content">
                    <div class="notif-meta">
                        <span class="notif-source">${escapeHtml(item.source)}</span>
                        <span class="notif-level">${isRead ? '已读' : notificationLevelText(item.level)}</span>
                    </div>
                    <p>${escapeHtml(item.message)}</p>
                    <div class="notif-bottom">
                        <small>${escapeHtml(item.time || '刚刚')}</small>
                        ${isRead ? '' : '<button type="button" class="notif-read-one">确认</button>'}
                    </div>
                </div>
            </div>
        `}).join('');
    }

    function buildDefaultNotifications() {
        return [
            { level: 'info', source: '运行值守', message: '当前无严重运行事件，保持 SCADA 链路与告警机组巡检。', time: '刚刚' },
        ];
    }

    async function refreshSystemNotifications() {
        const notifications = [];
        try {
            const [windfarmRes, scadaRes, workRes] = await Promise.all([
                fetch(`/api/windfarm/overview?t=${Date.now()}`),
                fetch(`/api/ops/scada/status?t=${Date.now()}`),
                fetch(`/api/ops/workorders?t=${Date.now()}`),
            ]);
            const windfarm = windfarmRes.ok ? await windfarmRes.json() : null;
            const scada = scadaRes.ok ? await scadaRes.json() : null;
            const work = workRes.ok ? await workRes.json() : null;

            if (windfarm?.summary) {
                const alarms = Number(windfarm.summary.alarm_count || 0);
                const running = Number(windfarm.summary.running_count || 0);
                const total = Number(windfarm.summary.turbine_count || 0);
                const avgHealth = Number(windfarm.summary.average_health || 0);
                if (alarms > 0) {
                    notifications.push({
                        level: alarms >= 3 ? 'critical' : 'warning',
                        source: '齿轮箱告警',
                        message: `${alarms} 台机组齿轮箱存在告警风险，运行 ${running}/${total}，建议先核查对应齿轮箱详情。`,
                        time: windfarm.timestamp || '刚刚',
                    });
                }
                if (avgHealth > 0 && avgHealth < 85) {
                    notifications.push({
                        level: 'warning',
                        source: '健康趋势',
                        message: `场站平均健康评分 ${avgHealth} 分，低于 85 分，建议生成健康趋势对比报告。`,
                        time: windfarm.timestamp || '刚刚',
                    });
                }
            }

            if (scada) {
                const quality = Number(scada.quality || 0);
                const latency = Number(scada.latency_ms || 0);
                const plcLost = Number(scada.plc_total || 0) - Number(scada.plc_online || 0);
                if (scada.status !== '在线' || quality < 98 || latency > 100 || plcLost > 0) {
                    notifications.push({
                        level: scada.status !== '在线' || plcLost > 0 ? 'critical' : 'warning',
                        source: 'SCADA 链路',
                        message: `${scada.gateway} ${scada.status}，PLC 离线 ${plcLost} 台，延迟 ${latency} ms，数据质量 ${quality}%。`,
                        time: scada.last_sync || '刚刚',
                    });
                }
            }

            if (work?.summary) {
                const overdue = Number(work.summary.overdue || 0);
                const open = Number(work.summary.open || 0);
                if (overdue > 0 || open >= 5) {
                    notifications.push({
                        level: overdue > 0 ? 'critical' : 'warning',
                        source: '检修工单',
                        message: overdue > 0
                            ? `${overdue} 条工单逾期，待处理 ${open} 条，请安排班组确认闭环计划。`
                            : `待处理工单 ${open} 条，请结合风险等级安排检修窗口。`,
                        time: '实时统计',
                    });
                }
            }

            if (!notifications.length) {
                notifications.push({
                    level: 'success',
                    source: '运行值守',
                    message: '当前无告警机组、无 SCADA 异常、无逾期工单。',
                    time: new Date().toLocaleTimeString('zh-CN', { hour12: false }),
                });
            }

            const nextNotifications = notifications.length ? notifications : buildDefaultNotifications();
            const nextSignature = JSON.stringify(nextNotifications.map(item => [item.level, item.source, item.message]));
            notificationSignature = nextSignature;
            systemNotifications = nextNotifications;
        } catch (error) {
            console.warn('Notification refresh failed:', error);
            const nextNotifications = buildDefaultNotifications();
            const nextSignature = JSON.stringify(nextNotifications.map(item => [item.level, item.source, item.message]));
            notificationSignature = nextSignature;
            systemNotifications = nextNotifications;
        }
        renderSystemNotifications();
    }

    function formatExpertAnswer(text) {
        const lines = String(text || '').split('\n');
        let currentSection = '';
        return lines.map(line => {
            const safeLine = escapeHtml(line.trim());
            if (!safeLine) return '<div class="qa-gap"></div>';
            const headingMatch = safeLine.match(/^(结论|风险等级|关键依据|建议步骤|后续追问|运维分析摘要)[:：](.*)$/);
            if (headingMatch) {
                currentSection = headingMatch[1];
                const rest = headingMatch[2].trim();
                const icon = {
                    结论: 'fa-circle-check',
                    风险等级: 'fa-triangle-exclamation',
                    关键依据: 'fa-list-check',
                    建议步骤: 'fa-screwdriver-wrench',
                    后续追问: 'fa-comments',
                    运维分析摘要: 'fa-clipboard-list',
                }[currentSection] || 'fa-circle-info';
                return `
                    <div class="qa-section-card ${currentSection === '风险等级' ? 'risk' : ''}">
                        <div class="qa-section-title"><i class="fa-solid ${icon}"></i>${currentSection}</div>
                        ${rest ? `<div class="qa-section-body">${rest}</div>` : ''}
                    </div>
                `;
            }
            if (/^\d+\./.test(safeLine)) return `<div class="qa-step"><b>${safeLine.split('.')[0]}</b><span>${safeLine.replace(/^\d+\.\s*/, '')}</span></div>`;
            if (safeLine.startsWith('- ') || safeLine.startsWith('•')) return `<div class="qa-bullet">${safeLine.replace(/^[-•]\s*/, '')}</div>`;
            if (currentSection) return `<div class="qa-line in-section">${safeLine}</div>`;
            return `<div class="qa-line">${safeLine}</div>`;
        }).join('');
    }

    function renderSourceBadges(sources = [], confidence = null, riskLevel = null, engine = null, apiStatus = null) {
        const badges = [];
        if (confidence !== null && confidence !== undefined) {
            badges.push(`<span class="qa-source-badge">置信度 ${(confidence * 100).toFixed(0)}%</span>`);
        }
        if (riskLevel) {
            badges.push(`<span class="qa-source-badge">风险 ${escapeHtml(riskLevel)}</span>`);
        }
        if (engine) {
            const engineLabel = engine === 'local_expert' || engine === 'local_fallback' ? '本地运维知识库' : '大模型辅助分析';
            badges.push(`<span class="qa-source-badge">${escapeHtml(engineLabel)}</span>`);
        }
        if (apiStatus) {
            badges.push(`<span class="qa-source-badge">${escapeHtml(apiStatus)}</span>`);
        }
        sources.slice(0, 3).forEach(source => {
            badges.push(`<span class="qa-source-badge">${escapeHtml(source.id)} ${escapeHtml(source.title)}</span>`);
        });
        return badges.length ? `<div class="qa-sources">${badges.join('')}</div>` : '';
    }

    function renderQaActionBar() {
        return `
            <div class="qa-followups qa-action-bar">
                <button class="suggest-btn" data-qa-nav="dashboard">查看实时趋势</button>
                <button class="suggest-btn" data-qa-nav="data">查看故障记录</button>
                <button class="suggest-btn" data-qa-nav="reports">生成健康报告</button>
            </div>
        `;
    }

    function renderFollowups(questions = []) {
        if (!questions.length) return '';
        return `<div class="qa-followups">${questions.map(question =>
            `<button class="suggest-btn" data-qa-followup="${escapeHtml(question)}">${escapeHtml(question)}</button>`
        ).join('')}</div>`;
    }

    function addMessage(text, isUser = false, meta = {}) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${isUser ? 'user-msg' : 'system-msg'} fade-in`;
        
        const avatarIcon = isUser ? '<i class="fa-solid fa-user"></i>' : '<i class="fa-solid fa-robot"></i>';
        const bubbleContent = isUser
            ? escapeHtml(text)
            : `${formatExpertAnswer(text)}${renderSourceBadges(meta.sources, meta.confidence, meta.riskLevel, meta.engine, meta.apiStatus)}${renderQaActionBar()}${renderFollowups(meta.suggestedQuestions)}`;
        
        msgDiv.innerHTML = `
            <div class="msg-avatar">${avatarIcon}</div>
            <div class="msg-bubble">${bubbleContent}</div>
        `;
        
        chatHistory.appendChild(msgDiv);
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }

    function createStreamingAssistantMessage() {
        const msgDiv = document.createElement('div');
        msgDiv.className = 'message system-msg fade-in';
        msgDiv.innerHTML = `
            <div class="msg-avatar"><i class="fa-solid fa-robot"></i></div>
            <div class="msg-bubble">
                <div class="qa-streaming-answer"><i class="fa-solid fa-circle-notch fa-spin"></i> 正在建立流式回答...</div>
            </div>
        `;
        chatHistory.appendChild(msgDiv);
        chatHistory.scrollTop = chatHistory.scrollHeight;
        return {
            message: msgDiv,
            bubble: msgDiv.querySelector('.msg-bubble'),
            streamBox: msgDiv.querySelector('.qa-streaming-answer')
        };
    }

    function appendStreamingText(streamBox, text) {
        if (!streamBox) return;
        if (streamBox.dataset.started !== 'true') {
            streamBox.dataset.started = 'true';
            streamBox.textContent = '';
        }
        streamBox.textContent += text;
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }

    function finalizeStreamingMessage(streaming, text, meta = {}) {
        if (!streaming?.bubble) return;
        streaming.bubble.innerHTML = `${formatExpertAnswer(text)}${renderSourceBadges(meta.sources, meta.confidence, meta.riskLevel, meta.engine, meta.apiStatus)}${renderQaActionBar()}${renderFollowups(meta.suggestedQuestions)}`;
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }

    function handleSseBlock(block, handlers) {
        const lines = block.split('\n').filter(Boolean);
        let event = 'message';
        const dataLines = [];
        lines.forEach(line => {
            if (line.startsWith('event:')) event = line.slice(6).trim();
            if (line.startsWith('data:')) dataLines.push(line.slice(5).trimStart());
        });
        if (!dataLines.length) return;
        let payload = {};
        try {
            payload = JSON.parse(dataLines.join('\n'));
        } catch (error) {
            payload = { text: dataLines.join('\n') };
        }
        handlers[event]?.(payload);
    }

    async function readSseResponse(response, handlers) {
        const reader = response.body?.getReader();
        if (!reader) throw new Error('stream reader unavailable');
        const decoder = new TextDecoder('utf-8');
        let buffer = '';
        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            const blocks = buffer.split('\n\n');
            buffer = blocks.pop() || '';
            blocks.forEach(block => handleSseBlock(block, handlers));
        }
        if (buffer.trim()) handleSseBlock(buffer, handlers);
    }

    latestStatus = { oil_temp: 65, vibration_rms: 2.5, oil_quality: 6, predicted_rul_days: 180, health_score: 85, power: 1200, acquisition_status: '在线' };

    function renderQaContext(status = latestStatus || {}) {
        const health = Number(status.health_score ?? 85);
        const statusText = status.acquisition_status || status.status_label || '实时同步';
        setText('qa-unit-id', selectedDetailUnit || '--');
        setText('qa-unit-status', statusText);
        setText('qa-oil-temp', status.oil_temp !== undefined ? `${Number(status.oil_temp).toFixed(1)} °C` : '--');
        setText('qa-vibration', status.vibration_rms !== undefined ? `${Number(status.vibration_rms).toFixed(2)} mm/s` : '--');
        setText('qa-oil-nas', status.oil_quality !== undefined ? `NAS ${status.oil_quality}` : '--');
        setText('qa-rul', status.predicted_rul_days !== undefined ? `${Math.floor(Number(status.predicted_rul_days))} 天` : '--');
        setText('qa-health', Number.isFinite(health) ? `${Math.round(health)} 分` : '--');
        setText('qa-power', status.power !== undefined ? `${Number(status.power).toFixed(0)} kW` : '--');
        setText('qa-context-mode', statusText);
    }

    function qaCurrentStatusPayload() {
        return {
            ...(latestStatus || {}),
            unit_id: selectedDetailUnit,
            selected_unit: selectedDetailUnit,
            timestamp: new Date().toISOString()
        };
    }

    renderQaContext(latestStatus);

    function dashboardStatusFromTurbineData(data = {}) {
        const unit = data.unit || {};
        const metrics = data.metrics || {};
        const life = data.life || {};
        const values = data.values || {};
        return {
            oil_temp: Number(unit.oil_temp ?? data.temperature?.gearbox ?? 0),
            vibration_rms: Number(unit.vibration_rms ?? 0),
            oil_quality: Number(values.oil_quality ?? unit.oil_quality ?? 6),
            predicted_rul_days: Number(life.rul_days ?? unit.rul_days ?? 0),
            health_score: Number(life.health_score ?? unit.health_score ?? 0),
            power: Number(metrics.active_power ?? unit.power_kw ?? 0),
            acquisition_status: unit.status_label || unit.status || '实时同步',
            status_label: unit.status_label,
            unit_id: unit.id || selectedDetailUnit,
            timestamp: data.scada_time || new Date().toISOString()
        };
    }

    async function syncQaSelectedUnit() {
        initQaUnitSelect();
        syncUnitSelectValue('qa-unit-select');
        renderQaContext({ ...latestStatus, acquisition_status: '同步中...' });
        try {
            const response = await fetch(`/api/windfarm/turbine/${encodeURIComponent(selectedDetailUnit)}?t=${Date.now()}`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const data = await response.json();
            latestTurbineDetail = data;
            latestStatus = { ...(latestStatus || {}), ...dashboardStatusFromTurbineData(data) };
            renderQaContext(latestStatus);
        } catch (error) {
            console.warn('QA unit sync failed:', error);
            renderQaContext({ ...latestStatus, acquisition_status: '同步失败' });
        }
    }

    async function sendQuestion(customQuestion = null) {
        const question = customQuestion || qaInput.value.trim();
        if (!question) return;

        addMessage(question, true);
        if (!customQuestion) qaInput.value = '';

        const deepThinking = qaDeepThinking ? qaDeepThinking.checked : true;
        const streaming = createStreamingAssistantMessage();
        let streamedAnswer = '';
        let streamMeta = {};

        try {
            const response = await fetch('/api/qa/ask_stream', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ 
                    question: question,
                    current_status: qaCurrentStatusPayload(),
                    deep_thinking: deepThinking,
                    answer_mode: deepThinking ? 'model_first' : 'local_only'
                })
            });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            await readSseResponse(response, {
                meta(payload) {
                    streamMeta = { ...streamMeta, ...payload };
                    if (streaming.streamBox && streaming.streamBox.dataset.started !== 'true') {
                        streaming.streamBox.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> 正在流式生成回答...';
                    }
                },
                delta(payload) {
                    const text = payload.text || '';
                    streamedAnswer += text;
                    appendStreamingText(streaming.streamBox, text);
                },
                done(payload) {
                    streamMeta = { ...streamMeta, ...payload };
                    streamedAnswer = payload.answer || streamedAnswer;
                },
                error(payload) {
                    throw new Error(payload.error || 'stream error');
                }
            });
            finalizeStreamingMessage(streaming, streamedAnswer, {
                sources: streamMeta.source_documents || streamMeta.sources || [],
                confidence: streamMeta.confidence,
                riskLevel: streamMeta.risk_level,
                suggestedQuestions: streamMeta.suggested_questions || [],
                engine: streamMeta.engine,
                apiStatus: streamMeta.api_status
            });
        } catch (error) {
            finalizeStreamingMessage(streaming, `结论：流式回答失败，请检查后端服务或大模型配置。\n\n关键依据：${error.message || '网络错误'}`, {
                engine: 'local_fallback',
                apiStatus: 'stream failed'
            });
        }
    }

    if (sendBtn && qaInput) {
        sendBtn.addEventListener('click', () => sendQuestion());
        qaInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendQuestion();
        });
    }

    window.askSuggested = (question) => {
        sendQuestion(question);
    };

    if (chatHistory) {
        chatHistory.addEventListener('click', (event) => {
            const followupBtn = event.target.closest('[data-qa-followup]');
            if (followupBtn) {
                sendQuestion(followupBtn.dataset.qaFollowup);
                return;
            }
            const navBtn = event.target.closest('[data-qa-nav]');
            if (navBtn) {
                document.querySelector(`[data-target="${navBtn.dataset.qaNav}"]`)?.click();
            }
        });
    }

    document.querySelector('.qa-prompt-board')?.addEventListener('click', (event) => {
        const button = event.target.closest('[data-qa-preset]');
        if (!button) return;
        const question = qaPresetQuestions[button.dataset.qaPreset];
        if (question) sendQuestion(question);
    });

    document.querySelector('.qa-workbench')?.addEventListener('click', (event) => {
        const navBtn = event.target.closest('[data-qa-nav]');
        if (!navBtn) return;
        document.querySelector(`[data-target="${navBtn.dataset.qaNav}"]`)?.click();
    });


    function initVibrationChart() {
        const chartDom = document.getElementById('vibration-chart');
        if (!chartDom || typeof echarts === 'undefined' || vibrationChart) return;

        vibrationChart = echarts.init(chartDom, null, { renderer: 'canvas' });
        const option = {
            backgroundColor: 'transparent',
            textStyle: { color: '#94a3b8' },
            tooltip: { trigger: 'axis' },
            grid: { left: '3%', right: '4%', bottom: '5%', top: '10%', containLabel: true },
            xAxis: { 
                type: 'category', 
                boundaryGap: false, 
                data: [],
                axisLine: { lineStyle: { color: 'rgba(255,255,255,0.2)' } },
                axisLabel: { color: '#94a3b8' }
            },
            yAxis: { 
                type: 'value',
                min: -1,
                max: 1,
                splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } },
                axisLine: { show: false },
                axisLabel: { color: '#94a3b8' }
            },
            series: [{
                name: '振动幅值',
                type: 'line',
                data: [],
                smooth: true,
                showSymbol: false,
                lineStyle: { width: 2, color: '#3b82f6' },
                areaStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: 'rgba(59, 130, 246, 0.4)' },
                        { offset: 1, color: 'rgba(59, 130, 246, 0.0)' }
                    ])
                }
            }]
        };
        vibrationChart.setOption(option);
        
        setTimeout(() => vibrationChart.resize(), 500);
    }

    initVibrationChart();

    function initDashboardCharts() {
        if (typeof echarts === 'undefined') return;

        const metricDom = document.getElementById('dashboard-metric-bar');
        if (metricDom && !dashboardMetricChart) {
            dashboardMetricChart = echarts.init(metricDom, 'dark', { renderer: 'canvas' });
            dashboardMetricChart.setOption({
                backgroundColor: 'transparent',
                tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
                grid: { left: 36, right: 16, top: 28, bottom: 32 },
                xAxis: {
                    type: 'category',
                    data: ['油温', '振动', '功率', 'RUL'],
                    axisLine: { lineStyle: { color: 'rgba(148,163,184,0.35)' } },
                    axisLabel: { color: '#cbd5e1' }
                },
                yAxis: {
                    type: 'value',
                    min: 0,
                    max: 120,
                    splitLine: { lineStyle: { color: 'rgba(148,163,184,0.12)' } },
                    axisLabel: { color: '#94a3b8', formatter: '{value}%' }
                },
                series: [{
                    name: '阈值占比',
                    type: 'bar',
                    barWidth: 28,
                    data: [],
                    itemStyle: {
                        borderRadius: [6, 6, 0, 0],
                        color: ({ value }) => value >= 100 ? '#ef4444' : (value >= 80 ? '#f59e0b' : '#22c55e')
                    },
                    markLine: {
                        symbol: 'none',
                        lineStyle: { color: 'rgba(245,158,11,0.65)', type: 'dashed' },
                        label: { color: '#fbbf24', formatter: '关注线' },
                        data: [{ yAxis: 80 }]
                    }
                }]
            });
        }

        const gaugeDom = document.getElementById('dashboard-health-gauge');
        if (gaugeDom && !dashboardHealthGauge) {
            dashboardHealthGauge = echarts.init(gaugeDom, 'dark', { renderer: 'canvas' });
            dashboardHealthGauge.setOption({
                backgroundColor: 'transparent',
                series: [{
                    type: 'gauge',
                    min: 0,
                    max: 100,
                    radius: '92%',
                    center: ['50%', '58%'],
                    progress: { show: true, width: 12, itemStyle: { color: '#22c55e' } },
                    axisLine: { lineStyle: { width: 12, color: [[0.6, '#ef4444'], [0.82, '#f59e0b'], [1, '#1e293b']] } },
                    axisTick: { show: false },
                    splitLine: { length: 8, lineStyle: { color: '#64748b', width: 1 } },
                    axisLabel: { color: '#94a3b8', distance: 16, fontSize: 10 },
                    pointer: { width: 4, itemStyle: { color: '#38bdf8' } },
                    detail: { formatter: '{value} 分', color: '#e2e8f0', fontSize: 24, fontWeight: 800, offsetCenter: [0, '56%'] },
                    data: [{ value: 0, name: '健康评分' }],
                    title: { color: '#94a3b8', fontSize: 12, offsetCenter: [0, '82%'] }
                }]
            });
        }

        const featureDom = document.getElementById('vibration-feature-chart');
        if (featureDom && !vibrationFeatureChart) {
            vibrationFeatureChart = echarts.init(featureDom, 'dark', { renderer: 'canvas' });
            vibrationFeatureChart.setOption({
                backgroundColor: 'transparent',
                tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
                grid: { left: 42, right: 18, top: 30, bottom: 32 },
                xAxis: {
                    type: 'category',
                    data: ['RMS', '峭度', '峰值因子'],
                    axisLine: { lineStyle: { color: 'rgba(148,163,184,0.35)' } },
                    axisLabel: { color: '#cbd5e1' }
                },
                yAxis: {
                    type: 'value',
                    splitLine: { lineStyle: { color: 'rgba(148,163,184,0.12)' } },
                    axisLabel: { color: '#94a3b8' }
                },
                series: [{
                    name: '当前值',
                    type: 'bar',
                    barWidth: 34,
                    data: [],
                    itemStyle: {
                        borderRadius: [6, 6, 0, 0],
                        color: ({ dataIndex }) => ['#38bdf8', '#a78bfa', '#f59e0b'][dataIndex] || '#38bdf8'
                    }
                }]
            });
        }
    }

    initDashboardCharts();

    const faultTypeColors = [
        '#38bdf8', '#f97316', '#ef4444', '#22c55e', '#a78bfa', '#facc15',
        '#fb7185', '#14b8a6', '#60a5fa', '#c084fc', '#f59e0b', '#94a3b8'
    ];

    function normalizeFaultTypeDistribution(items = []) {
        const sorted = [...items]
            .filter(item => item && item.name && Number(item.value) > 0)
            .sort((a, b) => Number(b.value) - Number(a.value));
        const visible = sorted.slice(0, 8).map((item, index) => ({
            name: item.name,
            value: Number(item.value),
            itemStyle: { color: faultTypeColors[index % faultTypeColors.length] }
        }));
        const otherValue = sorted.slice(8).reduce((sum, item) => sum + Number(item.value || 0), 0);
        if (otherValue > 0) {
            visible.push({
                name: '其他',
                value: otherValue,
                itemStyle: { color: faultTypeColors[visible.length % faultTypeColors.length] }
            });
        }
        return visible;
    }

    function renderFaultTypeBreakdown(items = []) {
        const box = document.getElementById('fault-type-breakdown');
        const totalBadge = document.getElementById('fault-type-total');
        if (!box) return;

        const normalized = normalizeFaultTypeDistribution(items);
        const total = normalized.reduce((sum, item) => sum + item.value, 0);
        if (totalBadge) totalBadge.innerText = `${total} 条记录`;

        if (!normalized.length || total <= 0) {
            box.innerHTML = '<div class="empty-breakdown">暂无故障类型统计</div>';
            return;
        }

        box.innerHTML = normalized.map((item) => {
            const color = item.itemStyle.color;
            const percent = total ? ((item.value / total) * 100) : 0;
            return `
                <div class="fault-type-row">
                    <div class="fault-type-row-main">
                        <div class="fault-type-name" title="${escapeHtml(item.name)}">
                            <span class="fault-type-dot" style="color:${color}; background:${color};"></span>
                            <span>${escapeHtml(item.name)}</span>
                        </div>
                        <div class="fault-type-bar"><span style="width:${percent.toFixed(1)}%; background:${color};"></span></div>
                    </div>
                    <div class="fault-type-value">
                        <strong>${item.value}</strong>
                        ${percent.toFixed(1)}%
                    </div>
                </div>
            `;
        }).join('');
    }

    window.addEventListener('resize', () => {
        [vibrationChart, trendLineChart, faultTypePieChart, severityBarChart, dashboardMetricChart, dashboardHealthGauge, vibrationFeatureChart].forEach(chart => {
            if (chart) chart.resize();
        });
        resizeDetailTurbine3D();
    });

    function initAnalysisCharts() {
        if (typeof echarts === 'undefined') return;

        const trendDom = document.getElementById('trend-line-chart');
        if (trendDom) {
            trendLineChart = echarts.init(trendDom, 'dark', { renderer: 'canvas' });
            trendLineChart.setOption({
                backgroundColor: 'transparent',
                tooltip: { trigger: 'axis' },
                grid: { left: '3%', right: '4%', bottom: '10%', containLabel: true },
                xAxis: { type: 'category', data: [], axisLine: { lineStyle: { color: '#94a3b8' } } },
                yAxis: { type: 'value', splitLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } } },
                series: [{
                    name: '故障频次',
                    type: 'line',
                    smooth: true,
                    data: [],
                    itemStyle: { color: '#3b82f6' },
                    areaStyle: {
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            { offset: 0, color: 'rgba(59, 130, 246, 0.4)' },
                            { offset: 1, color: 'rgba(59, 130, 246, 0)' }
                        ])
                    }
                }]
            });
        }

        const pieDom = document.getElementById('fault-type-pie-chart');
        if (pieDom) {
            faultTypePieChart = echarts.init(pieDom, 'dark', { renderer: 'canvas' });
            faultTypePieChart.setOption({
                backgroundColor: 'transparent',
                tooltip: {
                    trigger: 'item',
                    borderColor: 'rgba(148, 163, 184, 0.25)',
                    backgroundColor: 'rgba(15, 23, 42, 0.92)',
                    textStyle: { color: '#e2e8f0' },
                    formatter: '{b}<br/>记录数：{c}<br/>占比：{d}%'
                },
                legend: { show: false },
                title: {
                    text: '类型占比',
                    subtext: '前 8 类 + 其他',
                    left: 'center',
                    top: '42%',
                    textStyle: { color: '#e2e8f0', fontSize: 15, fontWeight: 700 },
                    subtextStyle: { color: '#94a3b8', fontSize: 11 }
                },
                series: [{
                    name: '故障类型',
                    type: 'pie',
                    radius: ['52%', '78%'],
                    center: ['50%', '50%'],
                    minAngle: 4,
                    avoidLabelOverlap: true,
                    itemStyle: {
                        borderRadius: 6,
                        borderColor: '#0f172a',
                        borderWidth: 2
                    },
                    label: {
                        show: true,
                        formatter: ({ percent }) => percent >= 8 ? `${percent.toFixed(0)}%` : '',
                        color: '#e2e8f0',
                        fontSize: 11
                    },
                    emphasis: {
                        scale: true,
                        scaleSize: 6,
                        label: { show: true, fontSize: 13, fontWeight: 'bold' }
                    },
                    labelLine: { length: 8, length2: 6 },
                    data: []
                }]
            });
        }

        const sevDom = document.getElementById('severity-bar-chart');
        if (sevDom) {
            severityBarChart = echarts.init(sevDom, 'dark', { renderer: 'canvas' });
            severityBarChart.setOption({
                backgroundColor: 'transparent',
                tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
                grid: { left: '5%', right: '5%', bottom: '15%', top: '15%', containLabel: true },
                xAxis: { type: 'category', data: [], axisLine: { lineStyle: { color: '#94a3b8' } } },
                yAxis: { type: 'value', splitLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } } },
                series: [{
                    name: '次数',
                    type: 'bar',
                    barWidth: '40%',
                    data: [],
                    itemStyle: {
                        borderRadius: [4, 4, 0, 0],
                        color: function(params) {
                            var colorList = {
                                '正常': '#10b981',
                                '警告': '#f59e0b',
                                '严重': '#ef4444'
                            };
                            return colorList[params.name] || '#3b82f6';
                        }
                    }
                }]
            });
        }
    }
    
    initAnalysisCharts();

    function getCurrentAnalysisDays() {
        return Number(document.querySelector('.range-btn.active')?.getAttribute('data-days') || 30);
    }

    async function fetchAnalysisData(days = 30) {
        try {
            const res = await fetch(`/api/data/trend?days=${encodeURIComponent(days)}&unit=${encodeURIComponent(selectedDetailUnit)}`);
            if (!res.ok) return;
            const data = await res.json();

            document.getElementById('ana-total').innerText = data.summary.total_faults;
            document.getElementById('ana-critical').innerText = data.summary.critical_faults;
            document.getElementById('ana-pending').innerText = data.summary.pending_faults;
            
            const healthRate = data.summary.total_faults === 0 ? 100 : 
                Math.max(0, 100 - (data.summary.critical_faults / data.summary.total_faults) * 100).toFixed(1);
            document.getElementById('ana-health-rate').innerText = `${healthRate}%`;
            
            const hrEl = document.getElementById('ana-health-rate');
            if (healthRate < 80) hrEl.style.color = 'var(--warning)';
            if (healthRate < 60) hrEl.style.color = 'var(--danger)';

            if (trendLineChart) {
                trendLineChart.setOption({
                    xAxis: { data: data.daily_trend.map(d => d.date) },
                    series: [{ data: data.daily_trend.map(d => d.count) }]
                });
            }

            if (faultTypePieChart) {
                const faultTypeData = normalizeFaultTypeDistribution(data.type_distribution);
                faultTypePieChart.setOption({
                    series: [{ data: faultTypeData }]
                });
            }
            renderFaultTypeBreakdown(data.type_distribution);

            if (severityBarChart) {
                severityBarChart.setOption({
                    xAxis: { data: data.severity_distribution.map(d => d.name) },
                    series: [{ data: data.severity_distribution.map(d => d.value) }]
                });
            }

            setTimeout(() => {
                if (trendLineChart) trendLineChart.resize();
                if (faultTypePieChart) faultTypePieChart.resize();
                if (severityBarChart) severityBarChart.resize();
            }, 300);
        } catch (error) { console.error('Failed to fetch analysis data:', error); }
    }

    const rangeBtns = document.querySelectorAll('.range-btn');
    rangeBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            rangeBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const days = btn.getAttribute('data-days');
            document.getElementById('trend-days-label').innerText = `近${days}天`;
            fetchAnalysisData(days);
        });
    });

    fetchAnalysisData(30);

    function setText(id, value) {
        const el = document.getElementById(id);
        if (el) el.innerText = value;
    }

    function buildUnitOptions() {
        return unitOptionsCache.map(item => {
            const label = item.is_custom ? `#${item.number} · ${item.id} · 新增` : `#${item.number} · ${item.id}`;
            return `<option value="${escapeHtml(item.id)}">${escapeHtml(label)}</option>`;
        }).join('');
    }

    function refreshUnitOptionCache(turbines = []) {
        if (!Array.isArray(turbines) || !turbines.length) return;
        unitOptionsCache = turbines
            .map(item => ({ id: item.id, number: item.number, is_custom: Boolean(item.is_custom) }))
            .sort((a, b) => Number(a.number) - Number(b.number));
        refreshUnitSelectors();
    }

    function refreshUnitSelectors() {
        ['dashboard-unit-select', 'diagnosis-unit-select', 'detail-unit-select', 'report-unit-select', 'qa-unit-select'].forEach(id => {
            const select = document.getElementById(id);
            if (!select || !select.dataset.ready) return;
            select.innerHTML = buildUnitOptions();
            select.value = selectedDetailUnit;
        });
        const faultSelect = document.getElementById('fault-unit-filter');
        if (faultSelect && faultSelect.dataset.ready) {
            const current = faultSelect.value || 'all';
            faultSelect.innerHTML = `<option value="all">全部机组</option>${buildUnitOptions()}`;
            faultSelect.value = [...faultSelect.options].some(option => option.value === current) ? current : 'all';
        }
    }

    function syncUnitSelectValue(id) {
        const select = document.getElementById(id);
        if (select) select.value = selectedDetailUnit;
    }

    function setSelectedUnit(unitId, options = {}) {
        selectedDetailUnit = unitId || 'WTG-001';
        setText('report-unit', selectedDetailUnit);
        syncUnitSelectValue('dashboard-unit-select');
        syncUnitSelectValue('diagnosis-unit-select');
        syncUnitSelectValue('detail-unit-select');
        syncUnitSelectValue('report-unit-select');
        syncUnitSelectValue('qa-unit-select');
        if (document.getElementById('dashboard')?.style.display !== 'none') {
            scheduleDashboardUnitSync();
        }
    }

    function setTrend(id, text, state = 'positive') {
        const el = document.getElementById(id);
        if (!el) return;
        el.className = `trend ${state}`;
        const icon = state === 'negative' ? 'fa-triangle-exclamation' : (state === 'warning' ? 'fa-circle-exclamation' : 'fa-circle-check');
        el.innerHTML = `<i class="fa-solid ${icon}"></i> ${text}`;
    }

    function updateDigitalTwinHeat(status) {
        if (!status || !THREE) return;
        const oilTemp = Number(status.oil_temp || 65);
        const vibration = Number(status.vibration_rms || 2.8);
        const oilQuality = Number(status.oil_quality || 6);
        const rulBase = Number(status.predicted_rul_days || 180);

        const componentModels = {
            housing: { name: '箱体油池', temp: oilTemp, wear: 0.6 + Math.max(0, oilQuality - 6) * 0.18, rul: rulBase + 50 },
            sun: { name: '行星级太阳轮', temp: oilTemp + vibration * 1.2, wear: 1.2 + vibration * 0.18, rul: rulBase + 20 },
            gear1: { name: '中间级大齿轮', temp: oilTemp + vibration * 1.6, wear: 1.0 + vibration * 0.22, rul: rulBase },
            gear2: { name: '高速级小齿轮', temp: oilTemp + vibration * 2.4 + Math.max(0, oilQuality - 7) * 0.8, wear: 1.8 + vibration * 0.35, rul: Math.max(7, rulBase - 35) },
            hs: { name: '高速轴承/输出轴', temp: oilTemp + vibration * 2.8, wear: 1.5 + vibration * 0.42, rul: Math.max(7, rulBase - 55) },
            ls: { name: '低速输入轴', temp: oilTemp + vibration * 0.9, wear: 0.8 + vibration * 0.12, rul: rulBase + 35 }
        };

        let hottest = { key: '', temp: 0, risk: 'normal' };
        Object.entries(componentModels).forEach(([key, model]) => {
            const risk = model.temp >= 85 || model.rul < 30 ? 'danger' : (model.temp >= 75 || model.rul < 90 ? 'warning' : 'normal');
            const mesh = twinComponents[key];
            const color = heatColor(model.temp);
            if (mesh && mesh.material) {
                mesh.material.color.copy(color);
                if (mesh.material.emissive) {
                    mesh.material.emissive.copy(color).multiplyScalar(risk === 'danger' ? 0.45 : (risk === 'warning' ? 0.25 : 0.08));
                }
                mesh.material.needsUpdate = true;
            }
            twinComponentState[key] = {
                ...model,
                temp: Number(model.temp.toFixed(1)),
                tempRise: Number(Math.max(0, model.temp - oilTemp).toFixed(1)),
                wear: Number(model.wear.toFixed(1)),
                rul: Math.floor(model.rul),
                risk
            };
            if (model.temp > hottest.temp) hottest = { key, temp: model.temp, risk };
            const hotspot = document.getElementById(`hotspot-${key}`);
            if (hotspot) {
                hotspot.className = `twin-hotspot ${risk === 'normal' ? '' : risk}`;
                const strong = hotspot.querySelector('strong');
                if (strong) strong.innerText = `${Math.round(model.temp)}°C`;
            }
            const fallbackPart = document.querySelector(`[data-twin-part="${key}"]`);
            if (fallbackPart) {
                fallbackPart.className = `twin-part twin-part-${key} ${risk === 'normal' ? '' : risk}`;
                const value = fallbackPart.querySelector('em');
                if (value) value.innerText = `${Math.round(model.temp)}°C`;
            }
        });

        const summary = document.getElementById('twin-summary');
        if (summary) {
            const state = twinComponentState[hottest.key] || {};
            summary.className = `twin-summary ${hottest.risk === 'normal' ? '' : hottest.risk}`;
            summary.innerText = `最高 ${state.name || '--'} ${Math.round(hottest.temp)}°C`;
        }

        if (selectedTwinComponent) refreshTwinOverlay(selectedTwinComponent);
    }

    function heatColor(temp) {
        const normalized = Math.max(0, Math.min(1, (temp - 55) / 40));
        const hue = 0.38 * (1 - normalized);
        return new THREE.Color().setHSL(hue, 0.95, 0.52);
    }

    function refreshTwinOverlay(key) {
        const overlay = document.getElementById('comp-info-overlay');
        if (!overlay || overlay.style.display === 'none') return;
        const state = twinComponentState[key];
        if (!state) return;
        document.getElementById('comp-name').innerText = state.name;
        document.getElementById('comp-wear').innerText = `${state.wear}%`;
        document.getElementById('comp-temp').innerText = `${state.temp}°C / +${state.tempRise} K`;
        document.getElementById('comp-rul').innerText = `${state.rul}d`;
        document.getElementById('comp-wear').className = state.risk === 'danger' ? 'status-tag danger' : (state.risk === 'warning' ? 'status-tag warning' : 'status-tag success');
    }

    function updateSensorList(sensors = []) {
        const list = document.getElementById('sensor-list');
        if (!list) return;
        list.innerHTML = sensors.map(sensor => {
            const rate = sensor.sample_rate >= 1000
                ? `${(sensor.sample_rate / 1000).toFixed(1)} kHz`
                : `${sensor.sample_rate} Hz`;
            return `
                <div class="sensor-row">
                    <div>
                        <strong>${escapeHtml(sensor.name)}</strong>
                        <span>${escapeHtml(sensor.id)} · ${escapeHtml(sensor.type)} · ${rate}</span>
                    </div>
                    <strong>${sensor.value ?? '--'} ${escapeHtml(sensor.unit)} <span class="sensor-status">${escapeHtml(sensor.status)}</span></strong>
                </div>
            `;
        }).join('');
    }

    function updateDashboardStatus(status, sensors = [], options = {}) {
        const updateKpi = options.updateKpi !== false;
        latestStatus = { ...status, sensors };
        updateDashboardVisualCharts(status);
        if (updateKpi) {
            setText('kpi-oil-temp', `${status.oil_temp} °C`);
            setText('kpi-vib-rms', `${status.vibration_rms} mm/s`);
            setText('kpi-power', `${status.power} kW`);
            setText('kpi-rul', `${Math.floor(status.predicted_rul_days || 0)} 天`);
            applyDashboardKpiStyle(status.oil_temp, status.vibration_rms, status.predicted_rul_days);

            setTrend('trend-oil-temp', status.oil_temp >= 85 ? '严重过温' : (status.oil_temp >= 75 ? '温度预警' : '温度正常'), status.oil_temp >= 85 ? 'negative' : (status.oil_temp >= 75 ? 'warning' : 'positive'));
            setTrend('trend-vib-rms', status.vibration_rms >= 6 ? '振动严重' : (status.vibration_rms >= 4.5 ? '振动预警' : '振动正常'), status.vibration_rms >= 6 ? 'negative' : (status.vibration_rms >= 4.5 ? 'warning' : 'positive'));
            setTrend('trend-power', status.power > 1000 ? '稳定并网' : '低负荷运行', status.power > 1000 ? 'positive' : 'warning');
            setTrend('trend-rul', status.predicted_rul_days < 30 ? '尽快复检' : (status.predicted_rul_days < 90 ? '跟踪退化' : '寿命充足'), status.predicted_rul_days < 30 ? 'negative' : (status.predicted_rul_days < 90 ? 'warning' : 'positive'));
        }

        setText('acq-status', status.acquisition_status || '在线');
        setText('acq-quality', `${status.data_quality ?? '--'}%`);
        setText('acq-sampling-rate', status.sampling_rate_hz ? `${(status.sampling_rate_hz / 1000).toFixed(1)} kHz` : '-- Hz');
        setText('acq-latency', `${status.latency_ms ?? '--'} ms`);
        setText('acq-packet-loss', `${status.packet_loss ?? '--'}%`);
        setText('acq-last-update', new Date((status.timestamp || Date.now() / 1000) * 1000).toLocaleTimeString());
        setText('acq-sample-count', `${status.sample_count ?? '--'} 帧`);
        setText('acq-sensor-count', `${status.online_sensors ?? sensors.length} / ${status.total_sensors ?? sensors.length}`);
        renderQaContext(status);

        const alertStrip = document.getElementById('dashboard-alert-strip');
        if (alertStrip) {
            const alerts = status.alert_items || [];
            alertStrip.className = `alert-strip ${alerts.some(item => item.level === '严重') ? 'danger' : (alerts.length ? 'warning' : '')}`;
            alertStrip.innerText = alerts.length ? alerts.map(item => `${item.level}: ${item.message}`).join('；') : '当前未发现实时告警。';
        }

        updateSensorList(sensors);
        updateDigitalTwinHeat(status);
    }

    function updateDashboardVisualCharts(status = {}) {
        initDashboardCharts();
        const oilTemp = Number(status.oil_temp || 0);
        const vibration = Number(status.vibration_rms || 0);
        const power = Math.max(0, Number(status.power || 0));
        const rul = Math.max(0, Number(status.predicted_rul_days || 0));
        const healthScore = Number(status.health_score ?? Math.max(35, Math.min(98, 55 + Math.min(rul, 240) / 6 - Math.max(0, vibration - 4.5) * 6 - Math.max(0, oilTemp - 75) * 0.6)));

        if (dashboardMetricChart) {
            dashboardMetricChart.setOption({
                series: [{
                    data: [
                        Number(Math.min(120, oilTemp / 85 * 100).toFixed(1)),
                        Number(Math.min(120, vibration / 7.1 * 100).toFixed(1)),
                        Number(Math.min(120, power / 1500 * 100).toFixed(1)),
                        Number(Math.min(120, rul / 180 * 100).toFixed(1))
                    ]
                }]
            });
        }

        if (dashboardHealthGauge) {
            const color = healthScore < 60 ? '#ef4444' : (healthScore < 82 ? '#f59e0b' : '#22c55e');
            dashboardHealthGauge.setOption({
                series: [{
                    progress: { itemStyle: { color } },
                    data: [{ value: Math.round(healthScore), name: '健康评分' }]
                }]
            });
        }
    }

    function applyDashboardKpiStyle(oilTemp, vibrationRms, rulDays) {
        const tempEl = document.getElementById('kpi-oil-temp');
        if (tempEl) {
            tempEl.style.color = oilTemp >= 85 ? 'var(--danger)' : (oilTemp >= 75 ? 'var(--warning)' : 'var(--accent-color)');
            tempEl.classList.toggle('pulse', oilTemp >= 85);
        }

        const vibEl = document.getElementById('kpi-vib-rms');
        if (vibEl) {
            vibEl.style.color = vibrationRms >= 6 ? 'var(--danger)' : (vibrationRms >= 4.5 ? 'var(--warning)' : 'var(--success)');
        }

        const rulEl = document.getElementById('kpi-rul');
        if (rulEl) {
            rulEl.style.color = rulDays < 30 ? 'var(--danger)' : (rulDays < 90 ? 'var(--warning)' : 'var(--success)');
        }
    }

    function healthScoreMeta(score) {
        const value = Math.max(0, Math.min(100, Number(score || 0)));
        if (value < 70) return { value, level: '风险', className: 'danger', color: '#ef4444' };
        if (value < 85) return { value, level: '关注', className: 'warning', color: '#f59e0b' };
        return { value, level: '健康', className: 'normal', color: '#22c55e' };
    }

    function updateDetailHealthScore(score) {
        const meta = healthScoreMeta(score);
        const card = document.querySelector('.health-summary-card');
        const ring = document.getElementById('td-health-ring');
        setText('td-health', `${Math.round(meta.value)} / 100`);
        setText('td-health-ring-value', `${Math.round(meta.value)}%`);
        setText('td-health-level', `${meta.level}状态 · 图形与评分同步`);
        if (card) {
            card.classList.remove('warning', 'danger');
            if (meta.className !== 'normal') card.classList.add(meta.className);
        }
        if (ring) {
            ring.style.setProperty('--score', meta.value);
            ring.style.setProperty('--score-color', meta.color);
        }
    }

    function dashboardStatusFromTurbine(data) {
        const unit = data?.unit || {};
        const metrics = data?.metrics || {};
        const life = data?.life || {};
        const alarms = data?.alarms || [];
        return {
            oil_temp: Number(unit.oil_temp ?? data?.temperature?.gearbox ?? 0),
            vibration_rms: Number(unit.vibration_rms ?? 0),
            power: Number(metrics.active_power ?? unit.power_kw ?? 0),
            predicted_rul_days: Number(life.rul_days ?? unit.rul_days ?? 0),
            health_score: Number(unit.health_score ?? life.health_score ?? latestStatus?.health_score ?? 85),
            oil_quality: unit.oil_quality ?? latestStatus?.oil_quality ?? 6,
            acquisition_status: latestStatus?.acquisition_status || '在线',
            data_quality: latestStatus?.data_quality,
            sampling_rate_hz: latestStatus?.sampling_rate_hz,
            latency_ms: latestStatus?.latency_ms,
            packet_loss: latestStatus?.packet_loss,
            timestamp: Date.now() / 1000,
            sample_count: latestStatus?.sample_count,
            online_sensors: latestStatus?.online_sensors,
            total_sensors: latestStatus?.total_sensors,
            alert_items: alarms.map(item => ({
                level: item.code === 'RUN-0' || item.code?.startsWith('DAQ') ? '正常' : '关注',
                message: `${item.code} ${item.status}`
            }))
        };
    }

    function makeTransparentMaterial(color, opacity = 0.35) {
        return new THREE.MeshStandardMaterial({
            color,
            transparent: true,
            opacity,
            roughness: 0.35,
            metalness: 0.25,
            depthWrite: false,
        });
    }

    function componentColor(level) {
        if (level === 'danger') return 0xef4444;
        if (level === 'warning') return 0xf59e0b;
        return 0x22c55e;
    }

    function componentLevel(item = {}) {
        const temp = Number(item.value || 0);
        if (item.level === 'danger' || temp >= 85) return 'danger';
        if (item.level === 'warning' || temp >= 75) return 'warning';
        return 'normal';
    }

    function renderNacelleCutaway(data) {
        const mount = document.getElementById('detail-turbine-3d');
        if (!mount || !data) return;
        const map = {};
        (data.component_state || []).forEach(item => { map[item.name] = item; });
        const cls = name => componentLevel(map[name]);
        const wind = Number(data.metrics?.wind_speed || data.unit?.wind_speed || 6);
        const power = Number(data.metrics?.active_power ?? data.unit?.power_kw ?? 0);
        const spin = Math.max(2.4, 8 - wind * 0.45).toFixed(2);
        const bladeAnimation = power <= 0
            ? ''
            : `<animateTransform attributeName="transform" attributeType="XML" type="rotate" from="0 178 160" to="360 178 160" dur="${spin}s" repeatCount="indefinite"/>`;

        mount.innerHTML = `
            <div class="cutaway-model" style="--detail-spin:${spin}s">
                <svg viewBox="0 0 860 340" role="img" aria-label="机舱剖视模型">
                    <defs>
                        <linearGradient id="cutShell" x1="0" x2="1">
                            <stop offset="0%" stop-color="#0ea5e9" stop-opacity="0.42"/>
                            <stop offset="46%" stop-color="#e0f2fe" stop-opacity="0.78"/>
                            <stop offset="100%" stop-color="#f8fafc" stop-opacity="0.92"/>
                        </linearGradient>
                        <linearGradient id="cutBlue" x1="0" x2="1">
                            <stop offset="0%" stop-color="#075985"/>
                            <stop offset="100%" stop-color="#22d3ee"/>
                        </linearGradient>
                        <filter id="cutGlow">
                            <feGaussianBlur stdDeviation="3.5" result="blur"/>
                            <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
                        </filter>
                    </defs>

                    <g class="cut-grid">
                        ${Array.from({ length: 15 }, (_, i) => `<line x1="${i * 60}" y1="0" x2="${i * 60}" y2="310"/>`).join('')}
                        ${Array.from({ length: 7 }, (_, i) => `<line x1="0" y1="${i * 50}" x2="860" y2="${i * 50}"/>`).join('')}
                    </g>

                    <g class="cut-rotor">
                        <ellipse cx="164" cy="160" rx="60" ry="82" class="cut-ring-depth"/>
                        <circle cx="178" cy="160" r="76" class="cut-ring-outer"/>
                        <circle cx="178" cy="160" r="53" class="cut-ring-inner"/>
                        <circle cx="178" cy="160" r="37" class="cut-ring-core"/>
                        <circle cx="178" cy="160" r="15" class="cut-hub ${cls('轮毂')}"/>
                        <g class="cut-blade-wheel">
                            ${bladeAnimation}
                            <path d="M178 160 C176 132, 174 103, 171 70"/>
                            <path d="M178 160 C151 172, 126 187, 100 205"/>
                            <path d="M178 160 C203 175, 224 195, 248 218"/>
                        </g>
                    </g>

                    <path class="cut-nacelle-shadow" d="M248 121 C296 92, 348 94, 395 117 L746 119 C786 121, 812 141, 824 164 C810 193, 783 209, 742 211 L394 211 C350 230, 294 227, 248 202 Z"/>
                    <path class="cut-nacelle-shell" d="M244 108 C290 83, 352 92, 395 113 L742 115 C785 117, 815 137, 826 164 C811 195, 784 213, 742 215 L393 215 C349 236, 288 231, 244 206 Z"/>
                    <path class="cut-window" d="M366 128 L742 128 C771 129, 792 142, 803 164 C790 185, 768 199, 736 199 L366 199 Z"/>
                    <path class="cut-upper-skin" d="M388 119 L736 121 C765 123, 787 137, 799 159 C746 147, 672 141, 592 140 L397 138 Z"/>
                    <path class="cut-blue-module" d="M245 113 C285 97, 330 97, 364 117 L364 209 C326 230, 286 229, 245 205 Z"/>
                    <rect x="374" y="113" width="56" height="104" rx="8" class="cut-dark-module"/>
                    <g class="cut-ring-lines">
                        <path d="M270 118 C294 109, 324 109, 352 121"/>
                        <path d="M270 201 C294 213, 324 213, 352 201"/>
                        <path d="M295 101 L295 221"/>
                    </g>

                    <line x1="230" y1="160" x2="397" y2="160" class="cut-shaft"/>
                    <circle cx="320" cy="160" r="18" class="cut-node ${cls('主轴承')}"/>
                    <rect x="424" y="144" width="54" height="42" rx="7" class="cut-device ${cls('齿轮箱')}"/>
                    <circle cx="522" cy="165" r="27" class="cut-device ${cls('发电机')}"/>
                    <rect x="607" y="141" width="42" height="48" rx="6" class="cut-device ${cls('变流器')}"/>
                    <g class="cut-gear-teeth">
                        ${Array.from({ length: 10 }, (_, i) => `<line x1="${431 + i * 4.4}" y1="141" x2="${431 + i * 4.4}" y2="136"/>`).join('')}
                        ${Array.from({ length: 10 }, (_, i) => `<line x1="${431 + i * 4.4}" y1="189" x2="${431 + i * 4.4}" y2="194"/>`).join('')}
                    </g>

                    <path d="M414 121 C488 80, 610 97, 720 147" class="cut-cable"/>
                    <path d="M414 121 C488 80, 610 97, 720 147" class="cut-cable-flow"/>
                    <path d="M435 209 L724 209" class="cut-platform"/>
                    <path d="M513 191 C560 191, 612 191, 660 191" class="cut-rail"/>
                    <g class="cut-stairs">
                        <path d="M573 209 L640 167"/>
                        <line x1="584" y1="202" x2="599" y2="202"/>
                        <line x1="599" y1="193" x2="614" y2="193"/>
                        <line x1="614" y1="183" x2="629" y2="183"/>
                        <line x1="629" y1="174" x2="644" y2="174"/>
                    </g>
                    <g class="cut-insulators">
                        <rect x="506" y="175" width="12" height="34" rx="5"/>
                        <rect x="532" y="175" width="12" height="34" rx="5"/>
                        <rect x="558" y="175" width="12" height="34" rx="5"/>
                        <rect x="584" y="175" width="12" height="34" rx="5"/>
                    </g>

                    <line x1="690" y1="119" x2="690" y2="208" class="cut-hoist-line"/>
                    <rect x="677" y="189" width="26" height="28" rx="4" class="cut-hoist"/>
                    <rect x="515" y="244" width="86" height="44" rx="5" class="cut-cabinet"/>
                </svg>
            </div>
        `;

        const legend = document.getElementById('detail-3d-legend');
        if (legend) {
            legend.innerHTML = '';
        }
    }

    function initDetailTurbine3D() {
        const mount = document.getElementById('detail-turbine-3d');
        if (!mount || detail3d || typeof THREE === 'undefined') return;
        mount.innerHTML = '';

        const scene3 = new THREE.Scene();
        const camera3 = new THREE.PerspectiveCamera(34, mount.clientWidth / Math.max(1, mount.clientHeight), 0.1, 1000);
        camera3.position.set(5.6, 1.8, 4.4);
        camera3.lookAt(0.48, 0.42, 0);

        const renderer3 = new THREE.WebGLRenderer({ antialias: true, alpha: true });
        renderer3.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
        renderer3.setSize(mount.clientWidth || 620, mount.clientHeight || 310);
        mount.appendChild(renderer3.domElement);

        scene3.add(new THREE.AmbientLight(0x93c5fd, 1.25));
        const keyLight = new THREE.DirectionalLight(0xffffff, 1.8);
        keyLight.position.set(5, 6, 4);
        scene3.add(keyLight);
        const rimLight = new THREE.PointLight(0x22d3ee, 1.6, 12);
        rimLight.position.set(-4, 2, 3);
        scene3.add(rimLight);

        const root = new THREE.Group();
        scene3.add(root);

        const nacelleShell = new THREE.Mesh(new THREE.CapsuleGeometry(0.55, 2.75, 8, 20), makeTransparentMaterial(0xdbeafe, 0.2));
        nacelleShell.rotation.z = Math.PI / 2;
        nacelleShell.scale.set(1.08, 0.68, 0.92);
        nacelleShell.position.set(0.62, 0.45, 0);
        root.add(nacelleShell);
        nacelleShell.add(new THREE.LineSegments(
            new THREE.EdgesGeometry(nacelleShell.geometry),
            new THREE.LineBasicMaterial({ color: 0x67e8f9, transparent: true, opacity: 0.58 })
        ));

        const cutawayPanel = new THREE.Mesh(
            new THREE.BoxGeometry(2.35, 0.035, 0.76),
            new THREE.MeshStandardMaterial({ color: 0xe0f2fe, transparent: true, opacity: 0.28, roughness: 0.38, metalness: 0.08 })
        );
        cutawayPanel.position.set(0.72, 0.17, 0.04);
        root.add(cutawayPanel);

        const nose = new THREE.Mesh(
            new THREE.ConeGeometry(0.38, 0.52, 28),
            makeTransparentMaterial(0xf8fafc, 0.36)
        );
        nose.rotation.z = -Math.PI / 2;
        nose.position.set(2.45, 0.45, 0);
        root.add(nose);

        const yawRing = new THREE.Mesh(
            new THREE.TorusGeometry(0.52, 0.085, 18, 72),
            makeTransparentMaterial(0x06b6d4, 0.64)
        );
        yawRing.position.set(-1.62, 0.45, 0);
        yawRing.rotation.y = Math.PI / 2;
        root.add(yawRing);

        const yawInner = new THREE.Mesh(
            new THREE.TorusGeometry(0.37, 0.032, 12, 60),
            new THREE.MeshStandardMaterial({ color: 0x38bdf8, transparent: true, opacity: 0.58, roughness: 0.25, metalness: 0.3 })
        );
        yawInner.position.copy(yawRing.position);
        yawInner.rotation.y = Math.PI / 2;
        root.add(yawInner);

        const hub = new THREE.Mesh(new THREE.SphereGeometry(0.2, 24, 16), new THREE.MeshStandardMaterial({ color: 0xe0f2fe, roughness: 0.25, metalness: 0.45 }));
        hub.position.set(-1.62, 0.45, 0);
        root.add(hub);

        const rotor = new THREE.Group();
        rotor.position.copy(hub.position);
        root.add(rotor);
        for (let i = 0; i < 3; i += 1) {
            const blade = new THREE.Mesh(new THREE.BoxGeometry(0.065, 1.08, 0.03), new THREE.MeshStandardMaterial({ color: 0x7dd3fc, roughness: 0.38, metalness: 0.12 }));
            blade.geometry.translate(0, 0.5, 0);
            blade.rotation.z = (Math.PI * 2 / 3) * i;
            rotor.add(blade);
        }

        const shaft = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.08, 1.35, 18), new THREE.MeshStandardMaterial({ color: 0xcbd5e1, roughness: 0.2, metalness: 0.7 }));
        shaft.rotation.z = Math.PI / 2;
        shaft.position.set(-0.84, 0.45, 0);
        root.add(shaft);

        const parts = {
            轮毂: hub,
            主轴承: new THREE.Mesh(new THREE.SphereGeometry(0.13, 20, 12), makeTransparentMaterial(0x22c55e, 0.74)),
            齿轮箱: new THREE.Mesh(new THREE.BoxGeometry(0.48, 0.42, 0.5), makeTransparentMaterial(0x22c55e, 0.68)),
            发电机: new THREE.Mesh(new THREE.CylinderGeometry(0.25, 0.25, 0.68, 32), makeTransparentMaterial(0x22c55e, 0.64)),
            变流器: new THREE.Mesh(new THREE.BoxGeometry(0.34, 0.34, 0.38), makeTransparentMaterial(0x22c55e, 0.62)),
        };
        parts.主轴承.position.set(-0.5, 0.45, 0);
        parts.齿轮箱.position.set(0.12, 0.45, 0);
        parts.发电机.position.set(0.88, 0.45, 0);
        parts.发电机.rotation.x = Math.PI / 2;
        parts.变流器.position.set(1.48, 0.28, 0.16);
        Object.values(parts).forEach(mesh => root.add(mesh));

        const brakeDisc = new THREE.Mesh(
            new THREE.CylinderGeometry(0.28, 0.28, 0.12, 32),
            new THREE.MeshStandardMaterial({ color: 0x0f172a, transparent: true, opacity: 0.82, roughness: 0.34, metalness: 0.45 })
        );
        brakeDisc.rotation.z = Math.PI / 2;
        brakeDisc.position.set(-0.22, 0.45, 0);
        root.add(brakeDisc);

        const cablePath = new THREE.CatmullRomCurve3([
            new THREE.Vector3(-0.08, 0.78, 0.08),
            new THREE.Vector3(0.45, 0.96, 0.08),
            new THREE.Vector3(1.16, 0.9, 0.04),
            new THREE.Vector3(1.86, 0.62, 0.02),
        ]);
        const cable = new THREE.Mesh(new THREE.TubeGeometry(cablePath, 42, 0.025, 10, false), new THREE.MeshStandardMaterial({ color: 0x22c55e, roughness: 0.35, metalness: 0.1 }));
        root.add(cable);

        const platform = new THREE.Mesh(new THREE.BoxGeometry(2.05, 0.05, 0.1), new THREE.MeshStandardMaterial({ color: 0xfacc15, roughness: 0.5, metalness: 0.15 }));
        platform.position.set(0.72, 0.02, 0.32);
        root.add(platform);

        const cabinets = new THREE.Group();
        for (let i = 0; i < 4; i += 1) {
            const insulator = new THREE.Mesh(
                new THREE.CylinderGeometry(0.045, 0.06, 0.28, 14),
                new THREE.MeshStandardMaterial({ color: 0x7dd3fc, transparent: true, opacity: 0.72, roughness: 0.32, metalness: 0.12 })
            );
            insulator.position.set(0.48 + i * 0.22, 0.11, 0.3);
            cabinets.add(insulator);
        }
        root.add(cabinets);

        const hookPost = new THREE.Mesh(new THREE.CylinderGeometry(0.022, 0.022, 0.52, 10), new THREE.MeshStandardMaterial({ color: 0xfacc15, roughness: 0.45, metalness: 0.1 }));
        hookPost.position.set(1.48, 0.48, 0.34);
        root.add(hookPost);
        const hookBox = new THREE.Mesh(new THREE.BoxGeometry(0.18, 0.18, 0.18), new THREE.MeshStandardMaterial({ color: 0xeab308, transparent: true, opacity: 0.72, roughness: 0.4, metalness: 0.1 }));
        hookBox.position.set(1.48, 0.18, 0.34);
        root.add(hookBox);

        const grid = new THREE.GridHelper(5, 10, 0x1d4ed8, 0x164e63);
        grid.position.y = -0.48;
        grid.material.transparent = true;
        grid.material.opacity = 0.22;
        scene3.add(grid);

        detail3d = { scene: scene3, camera: camera3, renderer: renderer3, root, rotor, parts, mount, speed: 0.018 };

        const animate = () => {
            if (!detail3d) return;
            detail3d.rotor.rotation.z += detail3d.speed;
            detail3d.root.rotation.y = Math.sin(Date.now() * 0.00045) * 0.08;
            detail3d.renderer.render(detail3d.scene, detail3d.camera);
            requestAnimationFrame(animate);
        };
        animate();
    }

    function updateDetailTurbine3D(data) {
        renderNacelleCutaway(data);
        return;
        initDetailTurbine3D();
        if (!detail3d || !data) return;
        const wind = Number(data.metrics?.wind_speed || data.unit?.wind_speed || 6);
        detail3d.speed = Math.max(0.006, Math.min(0.06, wind / 190));

        const componentMap = {};
        (data.component_state || []).forEach(item => { componentMap[item.name] = item; });
        Object.entries(detail3d.parts).forEach(([name, mesh]) => {
            const item = componentMap[name] || {};
            const temp = Number(item.value || 0);
            const level = item.level === 'warning' || temp >= 75 ? 'warning' : 'normal';
            const color = componentColor(level);
            mesh.material.color.setHex(color);
            mesh.material.emissive = new THREE.Color(color);
            mesh.material.emissiveIntensity = level === 'warning' ? 0.18 : 0.08;
        });

        const legend = document.getElementById('detail-3d-legend');
        if (legend) {
            legend.innerHTML = (data.component_state || []).map(item => {
                const temp = Number(item.value || 0);
                const level = item.level === 'warning' || temp >= 75 ? 'warning' : 'normal';
                return `<span class="detail-3d-chip ${level}"><i></i>${escapeHtml(item.name)} ${escapeHtml(item.value)}${escapeHtml(item.unit)}</span>`;
            }).join('');
        }
    }

    function resizeDetailTurbine3D() {
        if (!detail3d) return;
        const width = detail3d.mount.clientWidth || 620;
        const height = detail3d.mount.clientHeight || 310;
        detail3d.renderer.setSize(width, height);
        detail3d.camera.aspect = width / Math.max(1, height);
        detail3d.camera.updateProjectionMatrix();
    }

    function renderDashboardFromTurbine(data) {
        const displayData = data;
        const status = dashboardStatusFromTurbine(displayData);
        syncUnitSelectValue('dashboard-unit-select');
        updateDashboardStatus(status, latestStatus?.sensors || [], { updateKpi: true });
        const unitStatus = displayData?.unit?.status;
        setTrend('trend-power', displayData?.unit?.status_label || '当前机组', unitStatus === 'normal' ? 'positive' : (unitStatus === 'fault' ? 'negative' : 'warning'));
        setTrend('trend-rul', displayData?.life?.recheck_advice || '已同步当前机组', (displayData?.life?.recheck_interval_days || 90) <= 14 ? 'negative' : ((displayData?.life?.recheck_interval_days || 90) <= 30 ? 'warning' : 'positive'));
    }

    function updateVibrationChart(vibData) {
        if (!vibData || !vibData.time) return;
        if (!vibrationChart) initVibrationChart();
        initDashboardCharts();
        if (!vibrationChart) return;
        try {
            if (vibrationChart.getWidth() === 0) vibrationChart.resize();
            const features = vibData.features || {};
            if (vibrationFeatureChart) {
                vibrationFeatureChart.setOption({
                    series: [{
                        data: [
                            Number(features.rms || 0),
                            Number(features.kurtosis || 0),
                            Number(features.crest_factor || 0)
                        ]
                    }]
                });
            }
            vibrationChart.setOption({
                title: {
                    text: `RMS ${features.rms ?? '--'} | 峭度 ${features.kurtosis ?? '--'} | 峰值因子 ${features.crest_factor ?? '--'}`,
                    left: 8,
                    top: 0,
                    textStyle: { color: '#94a3b8', fontSize: 12, fontWeight: 400 }
                },
                xAxis: { data: vibData.time.map(t => (typeof t === 'number' ? `${t.toFixed(2)}s` : t)) },
                series: [{
                    data: isEnvelopeMode ? vibData.envelope : vibData.signal,
                    name: isEnvelopeMode ? '包络信号' : '原始信号',
                    lineStyle: { color: isEnvelopeMode ? '#f59e0b' : '#3b82f6' }
                }]
            }, false);
        } catch (err) {
            console.warn('Vibration chart update failed:', err);
        }
    }

    async function fetchDashboardData() {
        try {
            initDashboardUnitSelect();
            const statusRes = await fetch('/api/data/status');
            if (statusRes.ok) {
                const status = await statusRes.json();
                updateDashboardStatus(status, status.sensors || [], { updateKpi: false });
                scheduleDashboardUnitSync();
            }

            const vibRes = await fetch('/api/data/vibration');
            if (vibRes.ok) {
                updateVibrationChart(await vibRes.json());
            }
        } catch (error) { console.warn('Dashboard fetch error:', error); }
    }

    function applyAuthority(role) {
        const adminOnlyElements = [
            document.querySelector('.user-management-panel'),
            document.querySelector('#settings form button'),
            document.getElementById('goto-user-mgmt')
        ];
        
        if (role !== 'admin') {
            adminOnlyElements.forEach(el => {
                if (el) el.style.display = 'none';
            });
            const settingsHeader = document.querySelector('#settings h2');
            if (settingsHeader && !settingsHeader.querySelector('.readonly-label')) {
                settingsHeader.innerHTML += ' <small class="readonly-label" style="color:var(--text-secondary); font-size:0.5em;">(只读模式)</small>';
            }
        }
    }

    function updateSettingsProfile() {
        const tempWarning = Number(document.getElementById('config-temp-warning-threshold')?.value || 75);
        const temp = Number(document.getElementById('config-temp-threshold')?.value || 85);
        const vib = Number(document.getElementById('config-vibration-threshold')?.value || 4.5);
        const vibCritical = Number(document.getElementById('config-vibration-critical-threshold')?.value || 7.1);
        const oilWarning = Number(document.getElementById('config-oil-warning-threshold')?.value || 8);
        const oil = Number(document.getElementById('config-oil-quality-threshold')?.value || 10);
        const badge = document.getElementById('settings-risk-profile');
        if (!badge) return;

        let label = '常规保护';
        let cls = '';
        if (tempWarning <= 70 || temp <= 80 || vib <= 3.5 || vibCritical <= 6 || oilWarning <= 7 || oil <= 9) {
            label = '保守保护';
            cls = 'conservative';
        } else if (temp >= 90 || vib >= 6 || oil >= 12) {
            label = '宽松保护';
            cls = 'loose';
        }
        badge.textContent = label;
        badge.className = `settings-profile-badge ${cls}`;
        setText('settings-risk-summary', label);
        setText('temp-threshold-hint', temp >= 90 ? '当前油温阈值偏宽松，建议演示时说明风险控制策略。' : '推荐 75-85 °C，超过 85 °C 按严重过温处理。');
        setText('vibration-threshold-hint', vib >= 6 ? '当前振动阈值偏高，可能降低早期轴承异常敏感度。' : '推荐 4.5 mm/s，适合高速轴承与齿轮啮合异常预警。');
        setText('oil-threshold-hint', oil >= 12 ? '当前油液阈值偏宽松，建议加强油样复检频次。' : '推荐 NAS 10，超过阈值建议安排油液复检。');
    }

    async function fetchSettingsScadaSummary() {
        try {
            const res = await fetch(`/api/ops/scada/status?t=${Date.now()}`);
            if (!res.ok) return;
            const scada = await res.json();
            setText('settings-scada-brief', scada.status === '在线' ? `${scada.quality}%` : scada.status);
            setText('settings-scada-sync', `同步 ${scada.last_sync || '--'}`);
            setText('settings-gateway', scada.gateway || '--');
            setText('settings-protocols', Array.isArray(scada.protocols) ? scada.protocols.join(' / ') : '--');
            setText('settings-plc-online', `${scada.plc_online}/${scada.plc_total}`);
            setText('settings-latency', `${scada.latency_ms} ms`);
            setText('settings-quality', `${scada.quality}%`);
            setText('settings-sample-cycle', scada.data_format?.sample_cycle || '--');
            const state = document.getElementById('settings-access-state');
            if (state) {
                state.textContent = scada.status || '未知';
                state.className = `settings-profile-badge ${scada.status === '在线' ? 'conservative' : 'loose'}`;
            }
        } catch (error) {
            setText('settings-scada-brief', '离线');
            setText('settings-scada-sync', '接入状态读取失败');
        }
    }

    async function initSettingsView() {
        const configForm = document.getElementById('config-form');
        if (!configForm) return;

        bindSettingsTabs();
        const currentUser = JSON.parse(localStorage.getItem('currentUser') || '{}');
        setText('settings-current-role', currentUser.role === 'admin' ? 'Admin' : 'Operator');

        try {
            const response = await fetch('/api/settings/configs');
            const configs = await response.json();
            const tempWarnInput = document.getElementById('config-temp-warning-threshold');
            const tempInput = document.getElementById('config-temp-threshold');
            const vibInput = document.getElementById('config-vibration-threshold');
            const vibCriticalInput = document.getElementById('config-vibration-critical-threshold');
            const oilWarnInput = document.getElementById('config-oil-warning-threshold');
            const oilInput = document.getElementById('config-oil-quality-threshold');

            if (tempWarnInput) tempWarnInput.value = configs.temp_warning_threshold || 75;
            if (tempInput) tempInput.value = configs.temp_threshold || 85;
            if (vibInput) vibInput.value = configs.vibration_threshold || 4.5;
            if (vibCriticalInput) vibCriticalInput.value = configs.vibration_critical_threshold || 7.1;
            if (oilWarnInput) oilWarnInput.value = configs.oil_warning_threshold || 8;
            if (oilInput) oilInput.value = configs.oil_quality_threshold || 10;
            alarmThresholds = {
                temp_warning_threshold: Number(configs.temp_warning_threshold || 75),
                temp_threshold: Number(configs.temp_threshold || 85),
                vibration_threshold: Number(configs.vibration_threshold || 4.5),
                vibration_critical_threshold: Number(configs.vibration_critical_threshold || 7.1),
                oil_warning_threshold: Number(configs.oil_warning_threshold || 8),
                oil_quality_threshold: Number(configs.oil_quality_threshold || 10)
            };
            alarmThresholdsLoaded = true;
            localStorage.setItem('alarmThresholds', JSON.stringify(alarmThresholds));
            renderDetailThresholdEditor();
            updateSettingsProfile();
        } catch (e) { console.error('Failed to load configs'); }

        ['config-temp-warning-threshold', 'config-temp-threshold', 'config-vibration-threshold', 'config-vibration-critical-threshold', 'config-oil-warning-threshold', 'config-oil-quality-threshold'].forEach(id => {
            const input = document.getElementById(id);
            if (input && !input.dataset.boundSettings) {
                input.dataset.boundSettings = 'true';
                input.addEventListener('input', () => {
                    setText('settings-save-state', '有修改');
                    updateSettingsProfile();
                });
            }
        });

        const resetBtn = document.getElementById('reset-config-btn');
        if (resetBtn && !resetBtn.dataset.bound) {
            resetBtn.dataset.bound = 'true';
            resetBtn.addEventListener('click', () => {
                document.getElementById('config-temp-warning-threshold').value = 75;
                document.getElementById('config-temp-threshold').value = 85;
                document.getElementById('config-vibration-threshold').value = 4.5;
                document.getElementById('config-vibration-critical-threshold').value = 7.1;
                document.getElementById('config-oil-warning-threshold').value = 8;
                document.getElementById('config-oil-quality-threshold').value = 10;
                setText('settings-save-state', '已恢复推荐值');
                updateSettingsProfile();
                showActionToast('已恢复推荐阈值，请保存后生效');
            });
        }

        if (!configForm.dataset.bound) {
            configForm.dataset.bound = 'true';
            configForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                const payload = {
                    temp_warning_threshold: document.getElementById('config-temp-warning-threshold')?.value,
                    temp_threshold: document.getElementById('config-temp-threshold')?.value,
                    vibration_threshold: document.getElementById('config-vibration-threshold')?.value,
                    vibration_critical_threshold: document.getElementById('config-vibration-critical-threshold')?.value,
                    oil_warning_threshold: document.getElementById('config-oil-warning-threshold')?.value,
                    oil_quality_threshold: document.getElementById('config-oil-quality-threshold')?.value
                };
                if (Number(payload.temp_warning_threshold) >= Number(payload.temp_threshold) ||
                    Number(payload.vibration_threshold) >= Number(payload.vibration_critical_threshold) ||
                    Number(payload.oil_warning_threshold) >= Number(payload.oil_quality_threshold)) {
                    showActionToast('关注阈值必须小于告警阈值', 'warning');
                    setText('settings-save-state', '校验失败');
                    return;
                }

                try {
                    const res = await fetch('/api/settings/configs', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload)
                    });
                    const result = await res.json();
                    setText('settings-save-state', res.ok ? '已保存' : '保存失败');
                    if (res.ok) {
                        alarmThresholds = {
                            temp_warning_threshold: Number(payload.temp_warning_threshold || 75),
                            temp_threshold: Number(payload.temp_threshold || 85),
                            vibration_threshold: Number(payload.vibration_threshold || 4.5),
                            vibration_critical_threshold: Number(payload.vibration_critical_threshold || 7.1),
                            oil_warning_threshold: Number(payload.oil_warning_threshold || 8),
                            oil_quality_threshold: Number(payload.oil_quality_threshold || 10)
                        };
                        localStorage.setItem('alarmThresholds', JSON.stringify(alarmThresholds));
                        renderDetailThresholdEditor();
                        if (latestTurbineDetail) renderTurbineDetail(latestTurbineDetail);
                    }
                    showActionToast(result.message || (res.ok ? '系统参数已保存到数据库' : '保存失败'), res.ok ? 'success' : 'warning');
                } catch (err) {
                    setText('settings-save-state', '保存失败');
                    showActionToast('保存失败，请检查后端连接', 'warning');
                }
            });
        }

        fetchUserList();
        fetchSettingsScadaSummary();

        const addUserForm = document.getElementById('add-user-form');
        if (addUserForm && !addUserForm.dataset.bound) {
            addUserForm.dataset.bound = 'true';
            addUserForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                const username = document.getElementById('new-username').value;
                const password = document.getElementById('new-password').value;
                const role = document.getElementById('new-role').value;

                try {
                    const res = await fetch('/api/settings/users', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ username, password, role })
                    });
                    const result = await res.json();
                    if (res.ok) {
                        showActionToast(result.message || '新用户创建成功', 'success');
                        addUserForm.reset();
                        fetchUserList();
                    } else {
                        showActionToast(result.message || '创建失败', 'warning');
                    }
                } catch (err) {
                    showActionToast('网络错误，创建失败', 'warning');
                }
            });
        }
        
        const gotoBtn = document.getElementById('goto-user-mgmt');
        if (gotoBtn) {
            gotoBtn.onclick = () => {
                activateSettingsTab('users');
            };
        }
    }

    function activateSettingsTab(tabName) {
        document.querySelectorAll('[data-settings-tab]').forEach(button => {
            button.classList.toggle('active', button.dataset.settingsTab === tabName);
        });
        document.querySelectorAll('[data-settings-panel]').forEach(panel => {
            panel.classList.toggle('active', panel.dataset.settingsPanel === tabName);
        });
    }

    function bindSettingsTabs() {
        const tabs = document.getElementById('settings-tabs');
        if (!tabs || tabs.dataset.bound) return;
        tabs.dataset.bound = 'true';
        tabs.addEventListener('click', (event) => {
            const button = event.target.closest('[data-settings-tab]');
            if (!button) return;
            activateSettingsTab(button.dataset.settingsTab);
        });
    }


    async function fetchUserList() {
        const userListContainer = document.querySelector('.user-list-placeholder'); 
        if (!userListContainer) return;
        
        try {
            const res = await fetch('/api/settings/users');
            const users = await res.json();
            
            const admins = users.filter(u => u.role === 'admin').length;
            const operators = users.filter(u => u.role === 'operator').length;
            document.getElementById('admin-count').innerText = admins;
            document.getElementById('operator-count').innerText = operators;

            let html = `<div class="settings-user-list">
                <h4><i class="fa-solid fa-users"></i> 系统用户列表 <small style="color:var(--text-secondary); font-weight:500;">共 ${users.length} 人</small></h4>
                <div class="settings-user-list-scroll">`;
            
            users.forEach(u => {
                const isDefaultAdmin = u.username === 'admin';
                const currentUser = JSON.parse(localStorage.getItem('currentUser') || '{}');
                const isMe = u.username === currentUser.username;

                html += `<div class="settings-user-row">
                    <div class="settings-user-main">
                        <i class="fa-solid fa-user-circle" style="color:${isMe ? 'var(--accent-color)' : 'var(--text-secondary)'};"></i>
                        <div>
                            <strong>
                                ${u.username} 
                                <small>
                                    (${u.role === 'admin' ? '管理员' : '运维人员'})
                                </small>
                                ${isMe ? '<small style="color:var(--accent-color); margin-left:5px;">(我)</small>' : ''}
                            </strong>
                            <span class="badge ${u.role === 'admin' ? 'danger' : 'success'}" style="font-size:0.7rem; padding:1px 6px; margin-top:4px; display:inline-block;">
                                ${u.role === 'admin' ? '系统管理权限' : '标准运维权限'}
                            </span>
                        </div>
                    </div>
                    <div class="settings-user-actions">
                        ${(!isDefaultAdmin && !isMe) ? `
                            <button onclick="changeUserRole('${u.username}', '${u.role}')" class="primary-btn" style="background:rgba(255,255,255,0.1);">
                                <i class="fa-solid fa-arrows-rotate"></i> 切换权限
                            </button>
                            <button onclick="deleteUser('${u.username}')" class="primary-btn" style="background:rgba(239, 68, 68, 0.2); color:var(--danger);">
                                <i class="fa-solid fa-trash-can"></i>
                            </button>
                        ` : (isMe ? '<small style="color:var(--accent-color);">当前登录</small>' : '<small style="color:var(--text-secondary);">系统内置</small>')}
                    </div>
                </div>`;
            });
            html += '</div></div>';
            userListContainer.innerHTML = html;
        } catch (e) {
            console.error('Fetch user list error:', e);
        }
    }

    window.deleteUser = async (username) => {
        if (!confirm(`确定要删除用户 "${username}" 吗？此操作不可撤销。`)) return;
        try {
            const res = await fetch(`/api/settings/users/${username}`, { method: 'DELETE' });
            const data = await res.json();
            if (res.ok) {
                showActionToast(data.message || '用户已删除', 'success');
                fetchUserList();
            } else {
                showActionToast(data.message || '删除失败', 'warning');
            }
        } catch (e) { showActionToast('删除失败，网络错误', 'warning'); }
    };

    window.changeUserRole = async (username, currentRole) => {
        const newRole = currentRole === 'admin' ? 'operator' : 'admin';
        const userListContainer = document.querySelector('.user-list-placeholder');
        
        try {
            const res = await fetch(`/api/settings/users/${username}/role`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ role: newRole })
            });
            const data = await res.json();
            if (res.ok) {
                showActionToast(data.message || '用户权限已更新', 'success');
                fetchUserList();
            } else {
                showActionToast(data.message || '权限更新失败', 'warning');
            }
        } catch (e) { showActionToast('更新权限失败', 'warning'); }
    };



    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            const targetId = item.getAttribute('data-target');
            if (targetId === 'settings') {
                initSettingsView();
            } else if (targetId === 'reports') {
                fetchReport();
            } else if (targetId === 'dashboard') {
                setTimeout(() => {
                    window.dispatchEvent(new Event('resize'));
                }, 100);
            }
        });
    });

    async function fetchReport() {
        const reportArea = document.getElementById('printable-report');
        if (!reportArea) return;
        initReportUnitSelect();
        const rangeDays = document.getElementById('report-range-select')?.value || '30';
        
        try {
            const [response, unitResponse, trendResponse] = await Promise.all([
                fetch(`/api/report/generate?unit_id=${encodeURIComponent(selectedDetailUnit)}&days=${encodeURIComponent(rangeDays)}`),
                fetch(`/api/windfarm/turbine/${encodeURIComponent(selectedDetailUnit)}?t=${Date.now()}`),
                fetch(`/api/ops/trend-compare?unit_id=${encodeURIComponent(selectedDetailUnit)}&days=${encodeURIComponent(rangeDays)}`)
            ]);
            const data = await response.json();
            const unitData = unitResponse.ok ? await unitResponse.json() : null;
            const trendData = trendResponse.ok ? await trendResponse.json() : null;
            
            setText('report-unit', selectedDetailUnit);
            document.getElementById('report-id').innerText = data.report_id;
            document.getElementById('report-time').innerText = data.gen_time;
            setText('report-export-unit', selectedDetailUnit);
            setText('report-export-id', data.report_id);
            setText('report-export-time', data.gen_time);
            setText('report-export-range', `近 ${rangeDays} 天`);
            document.getElementById('rep-temp').innerText = unitData ? `${unitData.unit.oil_temp} °C` : data.detailed_metrics.average_oil_temp;
            document.getElementById('rep-vib').innerText = unitData ? `${unitData.unit.vibration_rms} mm/s` : data.detailed_metrics.vibration_rms_peak;
            document.getElementById('rep-oil').innerText = data.detailed_metrics.oil_quality_nas;
            document.getElementById('rep-pwr').innerText = unitData ? `${unitData.metrics.active_power} kW` : data.detailed_metrics.active_power;
            const qualityEl = document.getElementById('rep-quality');
            const reportRulEl = document.getElementById('rep-rul');
            const recheckEl = document.getElementById('rep-recheck');
            if (qualityEl) qualityEl.innerText = data.detailed_metrics.data_quality || '--';
            if (reportRulEl) reportRulEl.innerText = unitData ? `${unitData.life.rul_days} 天` : (data.detailed_metrics.predicted_rul || '--');
            if (recheckEl) recheckEl.innerText = unitData ? `${unitData.life.recheck_interval_days} 天（${unitData.life.recheck_level}）` : '--';
            const score = unitData ? unitData.life.health_score : data.health_score;
            document.getElementById('rep-score').innerText = score;
            document.getElementById('rep-diag-type').innerText = unitData ? unitData.unit.status_label : data.diagnosis_result.type;
            document.getElementById('rep-diag-advice').innerText = unitData ? `${unitData.unit.status_label}，健康 ${score} 分。` : data.summary;
            document.getElementById('rep-plan').innerText = unitData ? `${unitData.life.recheck_interval_days} 天复检，RUL ${unitData.life.rul_days} 天。` : data.maintenance_plan;
            setText('rep-trend', trendData?.conclusion || '趋势数据同步中。');
            setText('rep-workorder-action', score < 80 ? '建议生成 P2 检修工单并安排现场复核。' : '暂不生成工单，纳入月度趋势复核。');
            
            const scoreEl = document.getElementById('rep-score');
            if (score < 60) scoreEl.style.color = 'var(--danger)';
            else if (score < 80) scoreEl.style.color = 'var(--warning)';
            else scoreEl.style.color = 'var(--success)';
            
        } catch (e) { console.error('Failed to generate report'); }
    }

    const exportPdfBtn = document.getElementById('export-pdf-btn');
    if (exportPdfBtn) {
        exportPdfBtn.addEventListener('click', () => {
            exportReportKeyData();
        });
    }

    function exportReportKeyData() {
        const report = document.getElementById('printable-report');
        if (!report) return;
        const printWindow = window.open('', '_blank', 'width=980,height=720');
        if (!printWindow) {
            window.print();
            return;
        }
        printWindow.document.write(`
            <!doctype html>
            <html lang="zh-CN">
            <head>
                <meta charset="UTF-8">
                <title>${escapeHtml(document.getElementById('report-id')?.innerText || '健康关键数据报告')}</title>
                <style>
                    * { box-sizing: border-box; }
                    body { margin: 0; padding: 24px; color: #111827; background: #fff; font-family: Arial, "Microsoft YaHei", sans-serif; }
                    .report-content { max-width: 980px; margin: 0 auto; }
                    .report-export-header { display: flex; justify-content: space-between; gap: 16px; padding: 14px; margin-bottom: 12px; border: 1px solid #d1d5db; border-radius: 8px; }
                    .report-export-header h3 { margin: 0; font-size: 18px; }
                    .report-export-header div { display: flex; gap: 10px; flex-wrap: wrap; justify-content: flex-end; }
                    .report-export-header span, .report-key-card span, .report-score-card span, .report-conclusion-card span { display: block; color: #4b5563; font-size: 12px; margin-bottom: 6px; }
                    .report-export-header b { color: #111827; }
                    .report-key-grid { display: grid; grid-template-columns: 1.2fr repeat(4, 1fr); gap: 10px; }
                    .report-score-card, .report-key-card, .report-conclusion-card { border: 1px solid #d1d5db; border-radius: 8px; background: #fff; }
                    .report-score-card { grid-row: span 2; display: flex; flex-direction: column; justify-content: center; min-height: 150px; padding: 18px; }
                    .report-score-card strong { font-size: 48px; line-height: 1; color: #047857; }
                    .report-score-card small { margin-top: 8px; color: #111827; }
                    .report-key-card { min-height: 68px; padding: 12px; }
                    .report-key-card strong { font-size: 17px; }
                    .report-conclusion-card { display: grid; grid-template-columns: 1fr 1fr; gap: 0; margin-top: 10px; overflow: hidden; }
                    .report-conclusion-card > div { padding: 12px; border-right: 1px solid #d1d5db; }
                    .report-conclusion-card > div:last-child { border-right: 0; }
                    .report-conclusion-card strong { font-size: 14px; line-height: 1.5; }
                    @media print { body { padding: 0; } .report-content { max-width: none; } }
                </style>
            </head>
            <body>${report.outerHTML}</body>
            </html>
        `);
        printWindow.document.close();
        printWindow.focus();
        setTimeout(() => printWindow.print(), 250);
    }

    document.getElementById('refresh-report-btn')?.addEventListener('click', () => {
        fetchReport();
        showActionToast(`已刷新 ${selectedDetailUnit} 健康评估报告`);
    });
    document.getElementById('report-range-select')?.addEventListener('change', fetchReport);

    function renderWindfarmOverview(data) {
        if (!data) return;
        latestWindfarmData = data;
        refreshUnitOptionCache(data.turbines || []);
        setText('windfarm-name', data.windfarm || '齿轮箱健康管理总览');
        setText('windfarm-system', `${data.system || 'SL1500 齿轮箱多源状态监测'} · ${data.timestamp || '--'}`);
        const summary = data.summary || {};
        setText('wf-time-availability', summary.time_availability ?? '--');
        setText('wf-energy-availability', summary.energy_availability ?? '--');
        setText('wf-average-temp', summary.average_temp ?? '--');
        setText('wf-total-power', summary.total_power ?? '--');
        setText('wf-average-health', summary.average_health ?? '--');
        setText('wf-alarm-count', summary.alarm_count ?? '--');

        const legend = document.getElementById('windfarm-legend');
        if (legend && data.legend) {
            legend.innerHTML = '<span>图例</span>' + data.legend.map(item =>
                `<span class="legend-item"><i class="legend-dot ${escapeHtml(item.key)}"></i>${escapeHtml(item.legend)}</span>`
            ).join('');
        }

        const grid = document.getElementById('windfarm-grid');
        if (!grid) return;
        grid.classList.toggle('list-mode', windfarmViewMode === 'list');
        grid.innerHTML = (data.turbines || []).map(turbine => `
            <div class="turbine-card ${escapeHtml(turbine.status)}" data-unit="${escapeHtml(turbine.id)}">
                <div class="turbine-head">#${turbine.number}</div>
                <div class="turbine-body">
                    ${renderMiniTurbine(turbine)}
                    <div class="turbine-values">
                        <div><span>${turbine.power_kw}</span><span>kW</span></div>
                        <div><span>${turbine.wind_speed}</span><span>m/s</span></div>
                        <div><span>${turbine.oil_temp}°C</span><span>健康 ${turbine.health_score}</span></div>
                        <p class="turbine-state">${escapeHtml(turbine.status_label)}</p>
                    </div>
                </div>
            </div>
        `).join('');
    }

    function renderMiniTurbine(turbine) {
        return `
            <div class="mini-turbine" style="--spin-speed:${getTurbineSpinSpeed(turbine)}s" aria-label="${escapeHtml(turbine.status_label || '风机')}">
                <span class="mini-turbine-tower"></span>
                <span class="mini-turbine-nacelle"></span>
                <span class="mini-turbine-rotor">
                    <i></i><i></i><i></i>
                </span>
            </div>
        `;
    }

    function getTurbineSpinSpeed(turbine) {
        const status = turbine.status || 'standby';
        if (status === 'fault' || status === 'maintenance') return 0;
        if (status === 'standby') return 12;
        const wind = Number(turbine.wind_speed || 6);
        const baseSpeed = Math.max(1.4, 6.8 - wind * 0.42);
        return status === 'alarm' ? Math.max(2.2, baseSpeed + 1.2).toFixed(2) : baseSpeed.toFixed(2);
    }

    async function fetchWindfarmOverview() {
        try {
            const response = await fetch('/api/windfarm/overview');
            if (response.ok) renderWindfarmOverview(await response.json());
        } catch (error) {
            console.warn('Windfarm overview fetch failed:', error);
        }
    }

    function initDetailUnitSelect() {
        const select = document.getElementById('detail-unit-select');
        if (!select || select.dataset.ready) return;
        select.dataset.ready = 'true';
        select.innerHTML = buildUnitOptions();
        select.addEventListener('change', () => {
            setSelectedUnit(select.value);
            fetchTurbineDetail(selectedDetailUnit);
            fetchAnalysisData(getCurrentAnalysisDays());
        });
    }

    function initDashboardUnitSelect() {
        const select = document.getElementById('dashboard-unit-select');
        if (!select || select.dataset.ready) return;
        select.dataset.ready = 'true';
        select.innerHTML = buildUnitOptions();
        select.value = selectedDetailUnit;
        select.addEventListener('change', () => {
            setSelectedUnit(select.value);
            syncDashboardSelectedUnit();
            fetchAnalysisData(getCurrentAnalysisDays());
            showActionToast(`已切换实时监测机组：${selectedDetailUnit}`);
        });
    }

    function initDiagnosisUnitSelect() {
        const select = document.getElementById('diagnosis-unit-select');
        if (!select || select.dataset.ready) return;
        select.dataset.ready = 'true';
        select.innerHTML = buildUnitOptions();
        select.value = selectedDetailUnit;
        select.addEventListener('change', () => {
            setSelectedUnit(select.value);
            showActionToast(`已切换诊断机组：${selectedDetailUnit}`);
        });
    }

    function initReportUnitSelect() {
        const select = document.getElementById('report-unit-select');
        if (!select || select.dataset.ready) return;
        select.dataset.ready = 'true';
        select.innerHTML = buildUnitOptions();
        select.value = selectedDetailUnit;
        select.addEventListener('change', () => {
            setSelectedUnit(select.value);
            fetchReport();
        });
    }

    function initQaUnitSelect() {
        const select = document.getElementById('qa-unit-select');
        if (!select || select.dataset.ready) return;
        select.dataset.ready = 'true';
        select.innerHTML = buildUnitOptions();
        select.value = selectedDetailUnit;
        select.addEventListener('change', () => {
            setSelectedUnit(select.value);
            syncQaSelectedUnit();
            showActionToast(`已切换助手上下文机组：${selectedDetailUnit}`);
        });
    }

    function gearboxLevel(value, warning, danger) {
        const num = Number(value);
        if (!Number.isFinite(num)) return 'normal';
        if (num >= danger) return 'danger';
        if (num >= warning) return 'warning';
        return 'normal';
    }

    const thresholdMeta = {
        temp_warning_threshold: { label: '齿轮箱油温关注值', unit: '°C', min: 40, max: 120, step: 1 },
        temp_threshold: { label: '齿轮箱油温告警值', unit: '°C', min: 40, max: 120, step: 1 },
        vibration_threshold: { label: '振动 RMS 关注值', unit: 'mm/s', min: 0.5, max: 20, step: 0.1 },
        vibration_critical_threshold: { label: '振动 RMS 告警值', unit: 'mm/s', min: 0.5, max: 20, step: 0.1 },
        oil_warning_threshold: { label: '油液 NAS 关注值', unit: '级', min: 1, max: 16, step: 0.1 },
        oil_quality_threshold: { label: '油液 NAS 告警值', unit: '级', min: 1, max: 16, step: 0.1 }
    };

    function getThresholdLevels() {
        const tempWarning = Number(alarmThresholds.temp_warning_threshold || 75);
        const tempDanger = Number(alarmThresholds.temp_threshold || 85);
        const vibWarning = Number(alarmThresholds.vibration_threshold || 4.5);
        const vibDanger = Number(alarmThresholds.vibration_critical_threshold || 7.1);
        const oilWarning = Number(alarmThresholds.oil_warning_threshold || 8);
        const oilDanger = Number(alarmThresholds.oil_quality_threshold || 10);
        return {
            oilTempWarning: tempWarning,
            oilTempDanger: tempDanger,
            vibrationWarning: vibWarning,
            vibrationDanger: vibDanger,
            oilNasWarning: oilWarning,
            oilNasDanger: oilDanger
        };
    }

    async function loadAlarmThresholds(force = false) {
        if (alarmThresholdsLoaded && !force) {
            renderDetailThresholdEditor();
            return alarmThresholds;
        }
        try {
            const response = await fetch(`/api/settings/configs?t=${Date.now()}`);
            if (response.ok) {
                const configs = await response.json();
                alarmThresholds = {
                    temp_warning_threshold: Number(configs.temp_warning_threshold || 75),
                    temp_threshold: Number(configs.temp_threshold || 85),
                    vibration_threshold: Number(configs.vibration_threshold || 4.5),
                    vibration_critical_threshold: Number(configs.vibration_critical_threshold || 7.1),
                    oil_warning_threshold: Number(configs.oil_warning_threshold || 8),
                    oil_quality_threshold: Number(configs.oil_quality_threshold || 10)
                };
                localStorage.setItem('alarmThresholds', JSON.stringify(alarmThresholds));
            }
        } catch (error) {
            try {
                const cached = JSON.parse(localStorage.getItem('alarmThresholds') || '{}');
                alarmThresholds = { ...alarmThresholds, ...cached };
            } catch (_) {}
        }
        alarmThresholdsLoaded = true;
        renderDetailThresholdEditor();
        return alarmThresholds;
    }

    function renderDetailThresholdEditor() {
        const editor = document.getElementById('td-threshold-editor');
        if (!editor) return;
        const currentUser = JSON.parse(localStorage.getItem('currentUser') || '{}');
        const canEdit = currentUser.role === 'admin';
        const rows = Object.entries(thresholdMeta).map(([key, meta]) => {
            const value = Number(alarmThresholds[key] ?? 0);
            return `
                <div class="detail-threshold-row">
                    <span>${escapeHtml(meta.label)}</span>
                    ${canEdit
                        ? `<button type="button" class="threshold-edit-value" data-threshold-key="${key}">${escapeHtml(value.toString())} ${escapeHtml(meta.unit)}</button>`
                        : `<b class="threshold-readonly-value">${escapeHtml(value.toString())} ${escapeHtml(meta.unit)}</b>`}
                </div>
            `;
        }).join('');
        editor.innerHTML = `
            <h4>告警阈值</h4>
            ${rows}
            <small class="threshold-editor-note">${canEdit ? '点击数值可修改，回车或失焦保存。' : '当前账号为只读权限，管理员可修改阈值。'}</small>
        `;
    }

    async function saveAlarmThreshold(key, rawValue) {
        const currentUser = JSON.parse(localStorage.getItem('currentUser') || '{}');
        if (currentUser.role !== 'admin') {
            showActionToast('当前账号无阈值修改权限', 'warning');
            renderDetailThresholdEditor();
            return false;
        }
        const meta = thresholdMeta[key];
        if (!meta) return false;
        const value = Number(rawValue);
        if (!Number.isFinite(value) || value < meta.min || value > meta.max) {
            showActionToast(`${meta.label}需在 ${meta.min} - ${meta.max} ${meta.unit} 范围内`, 'warning');
            renderDetailThresholdEditor();
            return false;
        }
        alarmThresholds[key] = value;
        const nextLevels = getThresholdLevels();
        if (nextLevels.oilTempWarning >= nextLevels.oilTempDanger || nextLevels.vibrationWarning >= nextLevels.vibrationDanger || nextLevels.oilNasWarning >= nextLevels.oilNasDanger) {
            showActionToast('关注阈值必须小于告警阈值', 'warning');
            loadAlarmThresholds(true);
            return false;
        }
        localStorage.setItem('alarmThresholds', JSON.stringify(alarmThresholds));
        renderDetailThresholdEditor();
        try {
            const response = await fetch('/api/settings/configs', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ [key]: value })
            });
            if (!response.ok) throw new Error('save failed');
            const inputMap = {
                temp_warning_threshold: 'config-temp-warning-threshold',
                temp_threshold: 'config-temp-threshold',
                vibration_threshold: 'config-vibration-threshold',
                vibration_critical_threshold: 'config-vibration-critical-threshold',
                oil_warning_threshold: 'config-oil-warning-threshold',
                oil_quality_threshold: 'config-oil-quality-threshold'
            };
            const settingsInput = document.getElementById(inputMap[key]);
            if (settingsInput) settingsInput.value = value;
            updateSettingsProfile();
            showActionToast(`${meta.label}已更新`);
        } catch (error) {
            showActionToast('阈值已应用到当前页面，后端保存失败请稍后重试', 'warning');
        }
        if (latestTurbineDetail) renderTurbineDetail(latestTurbineDetail);
        return true;
    }

    function beginThresholdEdit(button) {
        const key = button.dataset.thresholdKey;
        const meta = thresholdMeta[key];
        if (!meta) return;
        const input = document.createElement('input');
        input.className = 'threshold-inline-input';
        input.type = 'number';
        input.min = meta.min;
        input.max = meta.max;
        input.step = meta.step;
        input.value = alarmThresholds[key];
        input.dataset.thresholdKey = key;
        button.replaceWith(input);
        input.focus();
        input.select();
    }

    function commitThresholdInput(input) {
        if (input.dataset.committed) return;
        input.dataset.committed = 'true';
        saveAlarmThreshold(input.dataset.thresholdKey, input.value);
    }

    function estimateOilNas(unit, temp, vibration) {
        const faultFactor = Math.min(3, Math.floor(Number(unit?.fault_count || 0) / 120));
        const tempFactor = Number(temp) >= 75 ? 2 : Number(temp) >= 68 ? 1 : 0;
        const vibFactor = Number(vibration) >= 6 ? 2 : Number(vibration) >= 4.5 ? 1 : 0;
        return Math.max(5, Math.min(12, 6 + faultFactor + tempFactor + vibFactor));
    }

    function setMetricState(id, level) {
        const card = document.getElementById(id)?.closest('div');
        if (!card) return;
        card.classList.remove('normal', 'warning', 'danger');
        card.classList.add(level || 'normal');
    }

    function buildGearboxAdvice(data, nasLevel) {
        const thresholds = getThresholdLevels();
        const unit = data.unit || {};
        const oilTemp = Number(data.temperature?.gearbox ?? unit.oil_temp ?? 0);
        const bearingTemp = Number(data.temperature?.bearing ?? 0);
        const vibration = Number(unit.vibration_rms ?? 0);
        const health = Number(data.life?.health_score ?? unit.health_score ?? 0);
        const advice = [];
        if (oilTemp >= thresholds.oilTempDanger) advice.push('油温达到告警值，优先检查油冷器、油泵、滤芯压差和油位，必要时申请停机点检。');
        else if (oilTemp >= thresholds.oilTempWarning) advice.push('油温进入关注区间，建议复核负荷、环境温度和冷却风扇运行状态。');
        if (bearingTemp >= 90) advice.push('高速轴承温度偏高，建议结合振动频谱判断轴承润滑或早期剥落风险。');
        if (vibration >= thresholds.vibrationDanger) advice.push('振动 RMS 超过告警阈值，建议开展 CMS 频谱、包络谱和齿轮啮合频率分析。');
        else if (vibration >= thresholds.vibrationWarning) advice.push('振动 RMS 接近关注阈值，建议缩短趋势复核周期并检查地脚、联轴器和齿面啮合状态。');
        if (nasLevel >= thresholds.oilNasWarning) advice.push('润滑油清洁度偏差，建议取油样复检 NAS 等级、水分和铁谱磨粒。');
        if (health < 70) advice.push('健康评分低于 70 分，建议生成严重告警并安排 24 小时内专项检查。');
        if (!advice.length) advice.push('当前齿轮箱油温、振动和寿命指标处于可控范围，按建议周期复检并持续跟踪趋势。');
        return advice;
    }

    function renderTurbineDetail(data) {
        if (!data || !data.unit) return;
        latestTurbineDetail = data;
        loadAlarmThresholds();
        const unit = data.unit;
        let metrics = { ...(data.metrics || {}) };
        setSelectedUnit(unit.id);
        const select = document.getElementById('detail-unit-select');
        if (select) select.value = unit.id;
        const displayData = { ...data, metrics };
        metrics = displayData.metrics || metrics;
        const temp = data.temperature || {};
        const oilTemp = temp.gearbox ?? unit.oil_temp;
        const bearingTemp = temp.bearing ?? '--';
        const vibration = unit.vibration_rms ?? '--';
        const oilNas = estimateOilNas(unit, oilTemp, vibration);

        setText('td-oil-temp', oilTemp ?? '--');
        setText('td-bearing-temp', bearingTemp);
        setText('td-vibration', vibration);
        setText('td-oil-nas', oilNas);
        setText('td-health-kpi', `${data.life?.health_score ?? '--'} 分`);
        setText('td-rul-kpi', `${data.life?.rul_days ?? '--'} 天`);
        setText('td-recheck-kpi', `${data.life?.recheck_interval_days ?? '--'} 天`);
        setText('td-fault-count', `${unit.fault_count ?? 0} 条`);
        const thresholds = getThresholdLevels();
        setMetricState('td-oil-temp', gearboxLevel(oilTemp, thresholds.oilTempWarning, thresholds.oilTempDanger));
        setMetricState('td-bearing-temp', gearboxLevel(bearingTemp, 80, 90));
        setMetricState('td-vibration', gearboxLevel(vibration, thresholds.vibrationWarning, thresholds.vibrationDanger));
        setMetricState('td-oil-nas', gearboxLevel(oilNas, thresholds.oilNasWarning, thresholds.oilNasDanger));
        setMetricState('td-health-kpi', Number(data.life?.health_score ?? 100) < 70 ? 'danger' : Number(data.life?.health_score ?? 100) < 85 ? 'warning' : 'normal');
        setMetricState('td-rul-kpi', Number(data.life?.rul_days ?? 999) < 90 ? 'danger' : Number(data.life?.rul_days ?? 999) < 180 ? 'warning' : 'normal');
        setMetricState('td-recheck-kpi', Number(data.life?.recheck_interval_days ?? 90) <= 14 ? 'danger' : Number(data.life?.recheck_interval_days ?? 90) <= 30 ? 'warning' : 'normal');
        setMetricState('td-fault-count', Number(unit.fault_count ?? 0) >= 100 ? 'warning' : 'normal');
        setText('td-unit-title', `#${unit.number}`);
        setText('td-unit-status', displayData.unit?.status_label || unit.status_label);
        updateDetailHealthScore(data.life?.health_score ?? unit.health_score ?? 0);
        setText('td-fan-years', `${data.life?.design_life_years ?? data.life?.fan_years ?? 20} 年 / ${data.life?.service_years ?? '--'} 年`);
        setText('td-life', `${data.life?.gearbox_months ?? '--'} 月 / RUL ${data.life?.rul_days ?? '--'} 天`);
        setText('td-recheck', `${data.life?.recheck_interval_days ?? '--'} 天（${data.life?.recheck_level ?? '--'}）`);
        setText('td-control-mode', unit.has_realtime ? 'SCADA/CMS 在线' : '仿真数据');
        setText('td-scada-time', data.scada_time || '--');

        const tempList = document.getElementById('td-temperature-list');
        if (tempList) {
            const rows = [
                ['齿轮箱油温(°C)', temp.gearbox],
                ['高速轴承温度(°C)', temp.bearing],
                ['振动 RMS(mm/s)', vibration],
                ['润滑油清洁度', `NAS ${oilNas}`],
            ];
            tempList.innerHTML = rows.map(([name, value]) => `
                <div class="temp-card">
                    <span>${escapeHtml(name)}</span>
                    <b>${escapeHtml(value ?? '--')}</b>
                </div>
            `).join('');
        }

        const adviceBox = document.getElementById('td-maintenance-advice');
        const adviceHtml = `
            <b>运维判定</b>
            ${buildGearboxAdvice(data, oilNas).map(item => `<span>${escapeHtml(item)}</span>`).join('')}
        `;
        if (adviceBox) {
            adviceBox.innerHTML = adviceHtml;
        }

        const alarmList = document.getElementById('td-alarm-list');
        if (alarmList) {
            const baseAlarms = data.alarms?.length
                ? data.alarms.map(item => `
                    <div class="alarm-item">
                        <b>${escapeHtml(item.code)}</b>
                        <span>
                            <strong>${escapeHtml(item.status)}</strong>
                            <small>${escapeHtml(item.time)}</small>
                        </span>
                    </div>
                `).join('')
                : '<div class="alarm-item normal"><b>OK</b><span><strong>当前无实时状态码和预警</strong><small>SCADA/CMS 持续在线监测</small></span></div>';
            alarmList.innerHTML = baseAlarms;
        }
        updateDetailAlarmPanel(data, adviceHtml);
    }

    function isRealDetailAlarm(item) {
        const code = String(item?.code || '').toUpperCase();
        const status = String(item?.status || '');
        if (!item) return false;
        if (code === 'OK' || code === 'RUN-0' || code === 'DAQ-0') return false;
        return !/正常|稳定|在线/.test(status);
    }

    function updateDetailAlarmPanel(data, adviceHtml) {
        const panel = document.getElementById('detail-alarm-panel');
        const timeEl = document.getElementById('detail-alarm-time');
        const alarmList = document.getElementById('td-alarm-list');
        const adviceBox = document.getElementById('td-maintenance-advice');
        if (!panel || !alarmList || !adviceBox) return;

        const realAlarms = (data.alarms || []).filter(isRealDetailAlarm);
        const unitStatus = data.unit?.status || '';
        const statusAlarm = ['alarm', 'fault', 'maintenance'].includes(unitStatus);
        const shownAlarms = realAlarms.length || statusAlarm
            ? (realAlarms.length ? realAlarms : (data.alarms || []))
            : [{ code: 'OK', status: '当前无告警，SCADA/CMS 持续监测', time: data.scada_time || '--', normal: true }];
        alarmList.innerHTML = shownAlarms.map(item => `
            <div class="alarm-item ${item.normal ? 'normal' : ''}">
                <b>${escapeHtml(item.code || 'ALARM')}</b>
                <span>
                    <strong>${escapeHtml(item.status || data.unit?.status_label || '状态告警')}</strong>
                    <small>${escapeHtml(item.time || data.scada_time || '--')}</small>
                </span>
                ${item.normal ? '' : `<button type="button" class="alarm-record-link" data-alarm-unit="${escapeHtml(data.unit?.id || selectedDetailUnit)}" data-alarm-key="${escapeHtml(item.code || item.status || '')}">查看记录</button>`}
            </div>
        `).join('');
        adviceBox.innerHTML = adviceHtml;
        if (timeEl) timeEl.textContent = data.scada_time || shownAlarms[0]?.time || '--';
        panel.style.display = 'grid';
    }

    async function fetchTurbineDetail(unitId = selectedDetailUnit) {
        initDetailUnitSelect();
        if (isTurbineDetailFetching) return;
        isTurbineDetailFetching = true;
        try {
            const response = await fetch(`/api/windfarm/turbine/${encodeURIComponent(unitId)}?t=${Date.now()}`);
            if (response.ok) renderTurbineDetail(await response.json());
        } catch (error) {
            console.warn('Turbine detail fetch failed:', error);
        } finally {
            isTurbineDetailFetching = false;
        }
    }

    function isViewVisible(id) {
        const el = document.getElementById(id);
        return !!el && el.style.display !== 'none';
    }

    function startTurbineDetailAutoRefresh() {
        stopTurbineDetailAutoRefresh();
        turbineDetailTimer = window.setInterval(() => {
            if (isViewVisible('turbine-detail')) {
                fetchTurbineDetail(selectedDetailUnit);
            }
        }, 5000);
    }

    function stopTurbineDetailAutoRefresh() {
        if (turbineDetailTimer) {
            window.clearInterval(turbineDetailTimer);
            turbineDetailTimer = null;
        }
    }

    async function syncDashboardSelectedUnit() {
        initDashboardUnitSelect();
        syncUnitSelectValue('dashboard-unit-select');
        try {
            const response = await fetch(`/api/windfarm/turbine/${encodeURIComponent(selectedDetailUnit)}?t=${Date.now()}`);
            if (!response.ok) return;
            const data = await response.json();
            if (latestTurbineDetail?.unit?.id === selectedDetailUnit) {
                latestTurbineDetail = data;
            }
            renderDashboardFromTurbine(data);
        } catch (error) {
            console.warn('Selected unit dashboard sync failed:', error);
        }
    }

    function scheduleDashboardUnitSync() {
        window.clearTimeout(dashboardSyncTimer);
        dashboardSyncTimer = window.setTimeout(() => {
            syncDashboardSelectedUnit();
        }, 120);
    }

    function shiftDetailUnit(delta) {
        const index = unitOptionsCache.findIndex(item => item.id === selectedDetailUnit);
        const currentIndex = index >= 0 ? index : 0;
        const nextIndex = (currentIndex + delta + unitOptionsCache.length) % unitOptionsCache.length;
        setSelectedUnit(unitOptionsCache[nextIndex]?.id || 'WTG-001');
        fetchTurbineDetail(selectedDetailUnit);
        fetchAnalysisData(getCurrentAnalysisDays());
    }

    function setWindfarmMode(mode) {
        windfarmViewMode = mode === 'list' ? 'list' : 'environment';
        document.getElementById('windfarm-env-mode')?.classList.toggle('active', windfarmViewMode === 'environment');
        document.getElementById('windfarm-list-mode')?.classList.toggle('active', windfarmViewMode === 'list');
        if (latestWindfarmData) renderWindfarmOverview(latestWindfarmData);
        showActionToast(windfarmViewMode === 'list' ? '已切换为列表模式' : '已切换为环境模式');
    }

    function openDetailTool(action) {
        if (action === 'hmi-login') {
            const url = `/hmi.html?unit=${encodeURIComponent(selectedDetailUnit)}&mode=login&return=detail`;
            window.open(url, '_blank', 'noopener');
            showActionToast(`已打开 ${selectedDetailUnit} HMI 运维控制台`);
            return;
        }
        if (action === 'report') {
            document.querySelector('[data-target="reports"]')?.click();
            showActionToast(`已打开 ${selectedDetailUnit} 的健康报告模块`);
            return;
        }
        if (action === 'trend') {
            document.querySelector('[data-target="dashboard"]')?.click();
            syncUnitSelectValue('dashboard-unit-select');
            showActionToast(`已切换到 ${selectedDetailUnit} 实时趋势`);
            return;
        }
        if (action === 'fullscreen') {
            const target = document.querySelector('.turbine-detail-shell');
            if (document.fullscreenElement) {
                document.exitFullscreen?.();
                showActionToast('已退出齿轮箱详情全屏');
            } else if (target?.requestFullscreen) {
                target.requestFullscreen();
                showActionToast('已进入齿轮箱详情全屏');
            } else {
                showActionToast('当前浏览器不支持全屏', 'warning');
            }
        }
    }

    function returnToTurbineDetail() {
        const sourceSelect =
            document.querySelector('#dashboard[style*="block"] #dashboard-unit-select') ||
            document.querySelector('#diagnosis[style*="block"] #diagnosis-unit-select') ||
            document.querySelector('#reports[style*="block"] #report-unit-select');
        if (sourceSelect?.value) {
            selectedDetailUnit = sourceSelect.value;
        }
        initDetailUnitSelect();
        syncUnitSelectValue('detail-unit-select');
        showView('turbine-detail');
        fetchTurbineDetail(selectedDetailUnit);
        showActionToast(`已返回 ${selectedDetailUnit} 齿轮箱详情`);
    }

    initDetailUnitSelect();
    document.getElementById('windfarm-env-mode')?.addEventListener('click', () => setWindfarmMode('environment'));
    document.getElementById('windfarm-list-mode')?.addEventListener('click', () => setWindfarmMode('list'));
    document.getElementById('windfarm-refresh')?.addEventListener('click', () => {
        fetchWindfarmOverview();
        showActionToast('齿轮箱健康总览数据已刷新');
    });
    document.getElementById('detail-prev-unit')?.addEventListener('click', () => shiftDetailUnit(-1));
    document.getElementById('detail-next-unit')?.addEventListener('click', () => shiftDetailUnit(1));
    document.getElementById('detail-back-windfarm')?.addEventListener('click', () => {
        document.querySelector('[data-target="windfarm"]')?.click();
    });
    document.getElementById('detail-breadcrumb-windfarm')?.addEventListener('click', () => {
        document.querySelector('[data-target="windfarm"]')?.click();
    });
    document.getElementById('detail-breadcrumb-current')?.addEventListener('click', () => {
        fetchTurbineDetail(selectedDetailUnit);
        showActionToast(`已刷新 ${selectedDetailUnit} 齿轮箱详情`);
    });
    document.addEventListener('click', (event) => {
        const thresholdButton = event.target.closest('.threshold-edit-value');
        if (thresholdButton) {
            beginThresholdEdit(thresholdButton);
            return;
        }

        const alarmRecordButton = event.target.closest('.alarm-record-link');
        if (alarmRecordButton) {
            openFaultDataForAlarm(alarmRecordButton.dataset.alarmUnit, alarmRecordButton.dataset.alarmKey);
            return;
        }

        const button = event.target.closest('button[data-health-action]');
        if (!button) return;
        const targetMap = {
            hmi: 'hmi-login',
            diagnosis: 'diagnosis',
            trend: 'dashboard',
            report: 'reports',
        };
        const target = targetMap[button.dataset.healthAction];
        if (target === 'hmi-login') {
            openDetailTool('hmi-login');
        } else if (target) {
            document.querySelector(`[data-target="${target}"]`)?.click();
        }
    });
    document.addEventListener('keydown', (event) => {
        if (!event.target.classList?.contains('threshold-inline-input')) return;
        if (event.key === 'Enter') {
            event.preventDefault();
            commitThresholdInput(event.target);
        }
        if (event.key === 'Escape') {
            renderDetailThresholdEditor();
        }
    });
    document.addEventListener('focusout', (event) => {
        if (!event.target.classList?.contains('threshold-inline-input')) return;
        commitThresholdInput(event.target);
    });
    document.addEventListener('click', (event) => {
        const button = event.target.closest('[data-return-detail]');
        if (!button) return;
        event.preventDefault();
        returnToTurbineDetail();
    });
    const windfarmGrid = document.getElementById('windfarm-grid');
    if (windfarmGrid) {
        windfarmGrid.addEventListener('click', (event) => {
            const card = event.target.closest('.turbine-card');
            if (!card) return;
            const unitId = card.dataset.unit || 'WTG-001';
            setSelectedUnit(unitId);
            document.querySelector('[data-target="turbine-detail"]')?.click();
            fetchTurbineDetail(unitId);
        });
    }

    loadAlarmThresholds();
    fetchDashboardData();
    fetchWindfarmOverview();

    const eventSource = new EventSource('/api/data/stream');
    
    eventSource.onmessage = (event) => {
        const payload = JSON.parse(event.data);
        updateDashboardStatus(payload.status, payload.sensors || [], { updateKpi: false });
        updateVibrationChart(payload.vibration);
        syncUnitSelectValue('dashboard-unit-select');
    };

    const toggleEnvelopeBtn = document.getElementById('toggle-envelope-btn');
    if (toggleEnvelopeBtn) {
        toggleEnvelopeBtn.addEventListener('click', () => {
            isEnvelopeMode = !isEnvelopeMode;
            toggleEnvelopeBtn.innerHTML = isEnvelopeMode ? 
                '<i class="fa-solid fa-microscope"></i> 查看原始波形' : 
                '<i class="fa-solid fa-wave-square"></i> 切换包络分析';
            toggleEnvelopeBtn.style.background = isEnvelopeMode ? 'rgba(245, 158, 11, 0.1)' : 'rgba(59, 130, 246, 0.1)';
            toggleEnvelopeBtn.style.borderColor = isEnvelopeMode ? '#f59e0b' : '#3b82f6';
            toggleEnvelopeBtn.style.color = isEnvelopeMode ? '#f59e0b' : '#3b82f6';
        });
    }

    eventSource.onerror = (err) => {
        console.warn("EventSource reconnecting:", err);
        fetchDashboardData();
    };

    const windfarmEventSource = new EventSource('/api/windfarm/stream');
    windfarmEventSource.onmessage = (event) => {
        renderWindfarmOverview(JSON.parse(event.data));
    };
    windfarmEventSource.onerror = () => {
        fetchWindfarmOverview();
    };


    const runDiagnosisBtn = document.getElementById('run-diagnosis-btn');
    if (runDiagnosisBtn) {
        runDiagnosisBtn.addEventListener('click', async () => {
            const statusSpan = document.getElementById('diagnosis-status');
            const resultsDiv = document.getElementById('diagnosis-results');
            
            statusSpan.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> 正在运行机器学习诊断模型...';
            statusSpan.style.color = 'var(--accent-color)';
            resultsDiv.style.display = 'none';

            try {
                const scenario = document.getElementById('diagnosis-scenario')?.value || 'auto';
                initDiagnosisUnitSelect();
                syncUnitSelectValue('diagnosis-unit-select');
                const response = await fetch(`/api/data/diagnosis?scenario=${encodeURIComponent(scenario)}&unit=${encodeURIComponent(selectedDetailUnit)}`);
                const data = await response.json();
                
                const stages = [
                    { msg: '执行油温残差分析 (M-IALO-SVR)...', time: 800 },
                    { msg: '执行 VMD 自适应参数寻优 (K=5, Alpha=2000)...', time: 1600 },
                    { msg: '基于包络阶次分析提取故障特征...', time: 2400 },
                    { msg: '计算小波散度健康指标 (SDD Indicator)...', time: 3200 }
                ];

                stages.forEach((stage, index) => {
                    setTimeout(() => {
                        statusSpan.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> ${stage.msg}`;
                    }, stage.time);
                });

                setTimeout(() => {
                    const features = data.features || {};
                    const explanation = data.explanation || {};
                    const persistence = data.persistence || {};
                    const riskFactors = explanation.top_risk_factors || [];
                    const workOrder = data.eam_work_order || null;
                    latestStatus = {
                        ...(latestStatus || {}),
                        ...(data.operating_snapshot || {}),
                        health_score: data.health_score,
                        predicted_rul_days: data.predicted_rul_days
                    };
                    statusSpan.innerHTML = '<i class="fa-solid fa-check"></i> 诊断完成';
                    statusSpan.style.color = 'var(--success)';

                    document.getElementById('fault-type').innerText = data.fault_type || '--';
                    document.getElementById('fault-risk-level').innerText = explanation.risk_level || '--';
                    document.getElementById('fault-component').innerText = data.fault_component || '--';
                    document.getElementById('fault-prob').innerText = data.probability ? (data.probability * 100).toFixed(2) + '%' : '--';
                    document.getElementById('fault-health-score').innerText = data.health_score ? `${data.health_score} / 100` : '--';
                    document.getElementById('fault-rul').innerText = data.predicted_rul_days ? `${data.predicted_rul_days} 天` : '--';
                    document.getElementById('fault-features').innerText = `RMS ${features.rms ?? '--'} | 峭度 ${features.kurtosis ?? '--'} | 峰值因子 ${features.crest_factor ?? '--'} | 包络峰值 ${features.envelope_peak ?? '--'}`;
                    document.getElementById('fault-risk-factors').innerHTML = riskFactors.length
                        ? riskFactors.map(item => `<span class="risk-factor-pill">${item.name}: ${item.score}%</span>`).join('')
                        : '--';
                    document.getElementById('fault-basis').innerText = explanation.diagnostic_basis || '--';
                    document.getElementById('fault-advice').innerText = data.advice || '--';
                    document.getElementById('fault-actions').innerHTML = (data.maintenance_actions || [])
                        .map(action => `<li>${action}</li>`).join('');
                    const workOrderWrap = document.getElementById('fault-work-order-wrap');
                    if (workOrder) {
                        workOrderWrap.style.display = 'block';
                        document.getElementById('fault-work-order').innerText = `${workOrder.order_number} | ${workOrder.priority} | ${workOrder.assigned_to} | ${workOrder.suggested_window}`;
                    } else {
                        workOrderWrap.style.display = 'none';
                    }
                    document.getElementById('fault-explanation').innerText = explanation.conclusion || '--';
                    document.getElementById('fault-persistence').innerText = persistence.message || '--';

                    const isNormal = data.severity === '正常' || data.fault_type === '正常运行';
                    document.getElementById('fault-type').style.color = isNormal ? 'var(--success)' : 'var(--danger)';
                    document.getElementById('fault-risk-level').style.color = isNormal ? 'var(--success)' : (data.severity === '警告' ? 'var(--warning)' : 'var(--danger)');

                    resultsDiv.style.display = 'block';
                    resultsDiv.classList.add('fade-in');
                    fetchFaultRecords();
                }, 4000);


            } catch (error) {
                statusSpan.innerHTML = '<i class="fa-solid fa-xmark"></i> 诊断失败: 无法连接服务器';
                statusSpan.style.color = 'var(--danger)';
            }
        });
    }
    
    const bell = document.getElementById('notification-bell');
    const dropdown = document.getElementById('notification-dropdown');
    if (bell && dropdown) {
        bell.addEventListener('click', (e) => {
            e.stopPropagation();
            dropdown.classList.toggle('active');
            if (dropdown.classList.contains('active')) {
                refreshSystemNotifications();
            }
        });
        
        document.addEventListener('click', () => {
            dropdown.classList.remove('active');
        });

        dropdown.addEventListener('click', (e) => {
            e.stopPropagation();
            const readBtn = e.target.closest('.notif-read-one');
            if (readBtn) {
                const item = readBtn.closest('.notif-item');
                const id = item?.getAttribute('data-notif-id');
                if (id) {
                    notificationReadIds.add(id);
                    renderSystemNotifications();
                    showActionToast('已确认该条运行通知');
                }
            }
        });

        document.getElementById('notif-mark-read')?.addEventListener('click', (e) => {
            e.stopPropagation();
            notificationsRead = true;
            systemNotifications.forEach(item => notificationReadIds.add(notificationId(item)));
            renderSystemNotifications();
            showActionToast('系统运行通知已全部标为已读');
        });

        refreshSystemNotifications();
        window.setInterval(refreshSystemNotifications, 60000);
    }

    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', () => {
            if (confirm('确定要退出系统吗？')) {
                document.getElementById('main-app').style.display = 'none';
                document.getElementById('login-overlay').style.display = 'flex';
                
                const loginForm = document.getElementById('login-form');
                if (loginForm) loginForm.reset();
                
                localStorage.removeItem('currentUser');
                
            }
        });
    }
});


