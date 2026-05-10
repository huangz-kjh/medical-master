/**
 * 字体图标加载检测与修复脚本
 * 该脚本检测Font Awesome是否正确加载，如果未加载则尝试使用备用方案
 */
(function () {
    // 当DOM加载完成后执行
    document.addEventListener('DOMContentLoaded', function () {
        setTimeout(function () {
            // 创建测试元素
            var iconTest = document.createElement('i');
            iconTest.className = 'fas fa-user';
            iconTest.style.visibility = 'hidden';
            document.body.appendChild(iconTest);

            // 获取计算样式并检查字体是否加载
            var computedStyle = window.getComputedStyle(iconTest);
            var isFontLoaded =
                computedStyle.fontFamily.includes('Font Awesome') ||
                computedStyle.fontFamily.includes('FontAwesome');

            if (!isFontLoaded) {
                // 尝试加载本地备用字体
                var backupCss = document.createElement('link');
                backupCss.rel = 'stylesheet';
                backupCss.href = '../static/download_style/css/font-awesome-4.7.0.min.css';
                document.head.appendChild(backupCss);

                // 添加第二套备用字体 - CDN方式
                var cdnCss = document.createElement('link');
                cdnCss.rel = 'stylesheet';
                cdnCss.href = 'https://cdn.jsdelivr.net/npm/font-awesome@4.7.0/css/font-awesome.min.css';
                document.head.appendChild(cdnCss);

                // 添加文本提示显示，仅在开发模式下
                if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
                    var alertDiv = document.createElement('div');
                    alertDiv.style.position = 'fixed';
                    alertDiv.style.top = '10px';
                    alertDiv.style.right = '10px';
                    alertDiv.style.background = 'rgba(255,255,0,0.8)';
                    alertDiv.style.padding = '10px';
                    alertDiv.style.borderRadius = '5px';
                    alertDiv.style.zIndex = '9999';
                    alertDiv.innerHTML = '字体图标加载失败，已切换到备用方案';
                    document.body.appendChild(alertDiv);

                    // 3秒后自动消失
                    setTimeout(function () {
                        alertDiv.style.opacity = '0';
                        alertDiv.style.transition = 'opacity 1s ease-in-out';
                        setTimeout(function () {
                            alertDiv.style.display = 'none';
                        }, 1000);
                    }, 3000);
                }

                // 添加基本CSS备用
                var fallbackStyle = document.createElement('style');
                fallbackStyle.textContent = `
                /* Font Awesome备用样式 - 当图标无法加载时使用 */
                .fa, .fas, .far, .fal, .fab {
                    display: inline-block;
                    font-style: normal;
                    font-variant: normal;
                    text-rendering: auto;
                    line-height: 1;
                    font-family: sans-serif;
                    -moz-osx-font-smoothing: grayscale;
                    -webkit-font-smoothing: antialiased;
                }
                .fa-home:before {
                    content: "🏠";
                }
                .fa-user:before {
                    content: "👤";
                }
                .fa-calendar:before, .fa-calendar-check:before, .fa-calendar-alt:before {
                    content: "📅";
                }
                .fa-cog:before, .fa-gear:before {
                    content: "⚙️";
                }
                .fa-search:before {
                    content: "🔍";
                }
                .fa-sign-out:before, .fa-sign-out-alt:before {
                    content: "🚪";
                }
                .fa-plus:before {
                    content: "+";
                }
                .fa-minus:before {
                    content: "-";
                }
                .fa-check:before {
                    content: "✓";
                }
                .fa-times:before {
                    content: "✕";
                }
                .fa-info:before, .fa-info-circle:before {
                    content: "ℹ️";
                }
                .fa-exclamation:before, .fa-exclamation-circle:before {
                    content: "⚠️";
                }
                .fa-spinner:before, .fa-sync:before, .fa-refresh:before {
                    content: "↻";
                }
                .fa-upload:before {
                    content: "⬆️";
                }
                .fa-download:before {
                    content: "⬇️";
                }
                .fa-chevron-left:before {
                    content: "◀";
                }
                .fa-chevron-right:before {
                    content: "▶";
                }
                .fa-chevron-up:before {
                    content: "▲";
                }
                .fa-chevron-down:before {
                    content: "▼";
                }
                .fa-bell:before {
                    content: "🔔";
                }
                .fa-envelope:before {
                    content: "✉️";
                }
                .fa-chart-bar:before, .fa-bar-chart:before {
                    content: "📊";
                }
                .fa-heart:before {
                    content: "❤️";
                }
                .fa-star:before {
                    content: "⭐";
                }
                .fa-file:before {
                    content: "📄";
                }
                .fa-folder:before {
                    content: "📁";
                }
                `;
                document.head.appendChild(fallbackStyle);

                // 二次检查
                setTimeout(function () {
                    // 清理原先的测试元素
                    document.body.removeChild(iconTest);

                    // 创建新的测试元素
                    var iconTest2 = document.createElement('i');
                    iconTest2.className = 'fas fa-user';
                    iconTest2.style.visibility = 'hidden';
                    document.body.appendChild(iconTest2);

                    var computedStyle2 = window.getComputedStyle(iconTest2);
                    var isFontLoaded2 =
                        computedStyle2.fontFamily.includes('Font Awesome') ||
                        computedStyle2.fontFamily.includes('FontAwesome');

                    document.body.removeChild(iconTest2);
                }, 1000);
            }
        }, 500);
    });
})();
