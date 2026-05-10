/**
 * Font Awesome 初始化脚本
 * 解决图标加载问题，确保图标能正确显示
 */
(function() {
    // 当页面DOM内容加载完成后执行
    document.addEventListener('DOMContentLoaded', function() {
        // 添加备用字体
        var link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = '../static/download_style/css/fa5-fix.css';
        document.head.appendChild(link);
        
        // 测试图标是否可见
        setTimeout(function() {
            // 测试 .fas 类的图标
            testAndFixIconVisibility('fas');
            
            // 测试 .fa 类的图标（用于Font Awesome 4）
            testAndFixIconVisibility('fa');
        }, 300);
    });
    
    // 测试并修复图标可见性
    function testAndFixIconVisibility(iconClass) {
        // 创建测试图标
        var testIcon = document.createElement('i');
        testIcon.className = iconClass + ' fa-user';
        testIcon.style.visibility = 'hidden';
        testIcon.style.position = 'absolute';
        testIcon.style.pointerEvents = 'none';
        document.body.appendChild(testIcon);
        
        // 检查图标的计算样式
        var computedStyle = window.getComputedStyle(testIcon);
        var fontFamily = computedStyle.fontFamily;
        var isFontLoaded = fontFamily.includes('Font Awesome') || 
                          fontFamily.includes('FontAwesome');
        
        // 检查字符宽度是否为0（无效字体）
        var hasWidth = testIcon.getBoundingClientRect().width > 0;
        
        // 如果图标无法显示，尝试修复
        if (!isFontLoaded || !hasWidth) {
            applyIconFixes(iconClass);
        }
        
        // 清理测试图标
        document.body.removeChild(testIcon);
    }
    
    // 应用图标修复方案
    function applyIconFixes(iconClass) {
        if (iconClass === 'fas') {
            // 应用 Font Awesome 5 Solid 修复
            loadCss('../static/download_style/css/font-awesome-4.7.0.min.css');
            loadCss('https://cdn.jsdelivr.net/npm/font-awesome@4.7.0/css/font-awesome.min.css');
            
            // 添加类转换 - 将 fas 映射到 fa
            mapIconClasses('fas', 'fa');
        } else if (iconClass === 'fa') {
            // 应用 Font Awesome 4 修复
            loadCss('https://cdn.jsdelivr.net/npm/font-awesome@4.7.0/css/font-awesome.min.css');
        }
        
        // 如果仍然没有加载成功，使用Unicode字符作为最终备用方案
        setTimeout(function() {
            var secondTestIcon = document.createElement('i');
            secondTestIcon.className = iconClass + ' fa-user';
            secondTestIcon.style.visibility = 'hidden';
            document.body.appendChild(secondTestIcon);
            
            var style = window.getComputedStyle(secondTestIcon);
            var isFontLoaded = style.fontFamily.includes('Font Awesome') || 
                              style.fontFamily.includes('FontAwesome');
            
            if (!isFontLoaded) {
                // 添加更简单的备用方案
                var fallbackStyle = document.createElement('style');
                fallbackStyle.textContent = `
                    .${iconClass}.fa-home:before { content: "🏠"; }
                    .${iconClass}.fa-user:before { content: "👤"; }
                    .${iconClass}.fa-calendar:before, 
                    .${iconClass}.fa-calendar-check:before, 
                    .${iconClass}.fa-calendar-alt:before { content: "📅"; }
                    .${iconClass}.fa-cog:before, 
                    .${iconClass}.fa-gear:before { content: "⚙️"; }
                    .${iconClass}.fa-search:before { content: "🔍"; }
                    .${iconClass}.fa-sign-out:before, 
                    .${iconClass}.fa-sign-out-alt:before { content: "🚪"; }
                    .${iconClass}.fa-plus:before { content: "+"; }
                    .${iconClass}.fa-minus:before { content: "-"; }
                    .${iconClass}.fa-check:before { content: "✓"; }
                    .${iconClass}.fa-times:before { content: "✕"; }
                    .${iconClass}.fa-spinner:before, 
                    .${iconClass}.fa-sync:before, 
                    .${iconClass}.fa-refresh:before { content: "↻"; }
                `;
                document.head.appendChild(fallbackStyle);
            }
            
            document.body.removeChild(secondTestIcon);
        }, 1000);
    }
    
    // 辅助函数：加载CSS
    function loadCss(url) {
        var link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = url;
        document.head.appendChild(link);
    }
    
    // 辅助函数：映射图标类
    function mapIconClasses(sourceClass, targetClass) {
        var style = document.createElement('style');
        style.textContent = `.${sourceClass} { font-family: '${targetClass}', 'FontAwesome', sans-serif !important; }`;
        document.head.appendChild(style);
        
        // 找到所有使用sourceClass的元素，添加targetClass
        setTimeout(function() {
            var elements = document.querySelectorAll('.' + sourceClass);
            for (var i = 0; i < elements.length; i++) {
                if (!elements[i].classList.contains(targetClass)) {
                    elements[i].classList.add(targetClass);
                }
            }
        }, 100);
    }
})(); 