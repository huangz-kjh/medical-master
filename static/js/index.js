// 全局变量
let isInitialized = false
let loadingTimeout = null
let longLoadingTimeout = null
let isDropdownOpen = false

// 使用iframe加载内容
function loadContent(url) {
  const iframe = document.getElementById('content-frame')
  const mainContent = document.querySelector('.main-content')

  // 1. 定义一个需要强制显示加载动画的页面列表（黑名单）
  const forceLoaderPages = ['/dashboard', '/doctor/appointments']

  // 2. 定义一个不需要加载动画的页面列表（白名单）
  const noLoaderPages = [
    '/patient/appointment',
    // 其他加载非常快的页面可以放在这里
  ]

  // 3. 重写判断逻辑
  let shouldShowLoader
  try {
    const urlPath = new URL(url, window.location.origin).pathname

    if (forceLoaderPages.includes(urlPath)) {
      shouldShowLoader = true // 如果在黑名单中，强制显示
    } else if (noLoaderPages.includes(urlPath)) {
      shouldShowLoader = false // 如果在白名单中，强制不显示
    } else {
      shouldShowLoader = true // 其他所有未指定的页面，默认都显示加载动画
    }
  } catch (e) {
    // 如果URL解析失败，默认显示加载动画
    shouldShowLoader = true
  }

  // 移除旧的加载动画
  const existingLoader = mainContent.querySelector('.iframe-loader')
  if (existingLoader) existingLoader.remove()

  // 预加载目标页面
  prefetchPage(url)

  let loader = null
  let messageInterval = null

  if (shouldShowLoader) {
    // 创建并显示加载动画（带进度条）
    loader = document.createElement('div')
    loader.className = 'iframe-loader'
    loader.style.zIndex = '10001'
    loader.innerHTML = `
        <div class="loader-animation">
            <span></span><span></span><span></span><span></span><span></span>
        </div>
        <div class="loader-message" id="loader-message">正在加载核心模块...</div>
    `
    mainContent.appendChild(loader)

    // 动态更新加载消息
    const loadingMessages = [
      '正在初始化智能分析引擎...',
      '正在连接影像数据库...',
      '正在准备3D可视化模块...',
      '正在守护您的数据安全...',
      '即将呈现工作台...',
      '优化数据渲染中...',
    ]
    messageInterval = setInterval(() => {
      const messageElement = document.getElementById('loader-message')
      if (messageElement) {
        const randomIndex = Math.floor(Math.random() * loadingMessages.length)
        messageElement.textContent = loadingMessages[randomIndex]
      }
    }, 2000) // 每2秒切换一次
  }

  // 隐藏iframe并加载新页面
  iframe.style.opacity = '0'
  iframe.dataset.currentUrl = url
  iframe.src = url

  showGlobalSkeleton()
  let skeleton = document.querySelector('.global-skeleton')
  if (skeleton) skeleton.style.zIndex = '9999'
  if (loader) loader.style.zIndex = '10001'

  // 加载完成
  iframe.onload = () => {
    if (messageInterval) clearInterval(messageInterval)
    // 添加一个短暂的延迟，确保动画至少能被看到，并且让过渡更平滑
    setTimeout(
      () => {
        if (loader) loader.remove()
        iframe.style.opacity = '1'
        updateActiveNavLink(url.split('?')[0])
        try {
          setupIframeLinks(iframe)
        } catch (e) {
          console.error(e)
        }
        hideGlobalSkeleton()
      },
      shouldShowLoader ? 300 : 0
    ) // 有加载器时延迟，否则不延迟
  }

  // 加载失败
  iframe.onerror = () => {
    if (messageInterval) clearInterval(messageInterval)
    if (loader) {
      loader.innerHTML =
        '<div class="loader-error"><i class="fas fa-exclamation-circle"></i><div>加载失败，请重试</div><button class="reload-btn" onclick="reloadCurrentPage()">重新加载</button></div>'
    }
    hideGlobalSkeleton()
  }
}

// 重新加载当前页面
function reloadCurrentPage() {
  const iframe = document.getElementById('content-frame')
  const currentUrl = iframe.dataset.currentUrl
  if (currentUrl) {
    loadContent(currentUrl)
  }
}

// 暴露给全局
window.reloadCurrentPage = reloadCurrentPage

// 处理iframe内部链接点击
function setupIframeLinks(iframe) {
  try {
    // 确保iframe已加载完成并具有可访问的内容
    if (!iframe.contentDocument || !iframe.contentWindow) return

    // 获取iframe内部所有链接
    const links = iframe.contentDocument.querySelectorAll('a[href]')

    links.forEach(link => {
      link.addEventListener('click', function (e) {
        // First, check for our special class to bypass this global handler
        if (this.classList.contains('no-global-load')) {
          // Allow the element's own event handlers to run
          return
        }

        const href = this.getAttribute('href')
        const target = this.getAttribute('target')

        if (!href || href.trim() === '' || href.startsWith('#') || href.startsWith('javascript:')) {
          e.preventDefault()
          return
        }

        // For external links or links meant for new tabs, allow default behavior
        if (target === '_blank' || !isSameOrigin(href)) {
          return
        }

        // If we've reached here, it's an internal link we should handle
        e.preventDefault()

        // In the main window, load the page into the iframe
        window.parent.loadContent(href)
      })
    })
  } catch (e) {
    console.error('处理iframe内部链接时出错:', e)
  }
}

function isSameOrigin(url) {
  try {
    const linkUrl = new URL(url, window.location.origin)
    return linkUrl.origin === window.location.origin
  } catch (e) {
    return false
  }
}

// 更新导航栏活动状态（忽略查询参数）
function updateActiveNavLink(url) {
  // 去除查询参数
  const path = url.split('?')[0]
  // 清除所有激活状态
  document.querySelectorAll('.nav-link').forEach(link => link.classList.remove('active'))
  // 匹配基础路径
  const activeLink = document.querySelector(`.nav-link[data-url="${path}"]`)
  if (activeLink) {
    activeLink.classList.add('active')
  }
}

// 切换用户下拉菜单
function toggleUserDropdown(show) {
  const dropdown = document.getElementById('userDropdown')

  // 如果找不到下拉菜单，不执行操作
  if (!dropdown) {
    console.warn('用户下拉菜单元素未找到')
    return
  }

  if (show === undefined) {
    show = !isDropdownOpen
  }

  isDropdownOpen = show

  if (show) {
    // 显示用户菜单
    dropdown.style.opacity = '1'
    dropdown.style.visibility = 'visible'
    dropdown.style.transform = 'translateY(0)'
    dropdown.style.pointerEvents = 'auto'

    // 添加force-show类强制显示
    dropdown.classList.add('force-show')

    // 使用setTimeout确保CSS过渡效果正常工作
    setTimeout(() => {
      dropdown.classList.add('active')
    }, 10)
  } else {
    // 隐藏用户菜单
    dropdown.classList.remove('active')
    dropdown.style.opacity = '0'
    dropdown.style.visibility = 'hidden'
    dropdown.style.transform = 'translateY(10px)'
    dropdown.style.pointerEvents = 'none'
  }
}

// 页面加载完成后执行初始化
document.addEventListener('DOMContentLoaded', function () {
  // 检查UI元素完整性
  checkUIComponents()

  // 初始化应用
  initializeApp()

  // 初始化通知功能
  optimizedInitNotifications()

  // 初始化用户菜单 - 确保在所有角色页面上都能正确工作
  initUserMenu()

  // 特别处理顶部导航栏用户菜单
  fixTopNavUserMenu()
})

// 检查UI元素是否完整
function checkUIComponents() {
  const components = {
    userAvatar: document.getElementById('userAvatar'),
    userDropdown: document.getElementById('userDropdown'),
    notificationIcon: document.getElementById('notificationIcon'),
    notificationBadge: document.getElementById('notificationBadge'),
    notificationDropdown: document.getElementById('notificationDropdown'),
    notificationList: document.getElementById('notificationList'),
    markAllReadBtn: document.getElementById('markAllReadBtn'),
    userRole: document.getElementById('user-role'),
  }

  if (!components.userAvatar) {
    console.error('用户头像组件未找到')
  }

  if (!components.userDropdown) {
    console.error('用户菜单组件未找到')
  } else {
    // 确保用户菜单初始状态为隐藏
    components.userDropdown.style.display = 'none'
    components.userDropdown.style.visibility = 'hidden'
    components.userDropdown.classList.remove('active')
  }

  if (!components.notificationIcon) {
    console.error('通知图标组件未找到')
  }

  if (components.userRole) {
    console.log('当前用户角色:', components.userRole.textContent.trim())
  } else {
    console.warn('无法确定当前用户角色')
  }
}

// 初始化函数
function initializeApp() {
  if (isInitialized) return
  isInitialized = true

  // 初始化导航链接
  document.querySelectorAll('.nav-link').forEach(link => {
    link.addEventListener('click', function (e) {
      e.preventDefault()
      const url = this.dataset.url
      if (url) {
        loadContent(url)
        updateActiveNavLink(url)
      }
    })
  })

  // 从URL或localStorage加载初始页面
  const params = new URLSearchParams(window.location.search)
  const page = params.get('page')
  const lastPage = localStorage.getItem('lastActivePage') || '/dashboard' // 默认仪表盘
  const initialPage = page || lastPage

  // 加载初始内容
  loadContent(initialPage)
  updateActiveNavLink(initialPage)

  // 保存当前页面到localStorage
  window.addEventListener('beforeunload', () => {
    const iframe = document.getElementById('content-frame')
    if (iframe && iframe.dataset.currentUrl) {
      localStorage.setItem('lastActivePage', iframe.dataset.currentUrl)
    }
  })

  // 处理iframe高度自适应
  adjustFrameHeight()
  window.addEventListener('resize', adjustFrameHeight)

  // 修复用户菜单，使其在主页加载时也能正常工作
  fixTopNavUserMenu()
}

function adjustFrameHeight() {
  const iframe = document.getElementById('content-frame')
  const headerHeight = document.querySelector('header').offsetHeight
  iframe.style.height = `calc(100vh - ${headerHeight}px)`
}

// 初始化用户菜单 - 专门的函数确保在所有角色页面上都能正确工作
function initUserMenu() {
  const userAvatar = document.getElementById('userAvatar')
  const userDropdown = document.getElementById('userDropdown')

  if (!userAvatar || !userDropdown) {
    console.warn('用户菜单元素未找到')
    return
  }

  // 确保用户下拉菜单初始状态正确
  userDropdown.style.opacity = '0'
  userDropdown.style.visibility = 'hidden'
  userDropdown.style.transform = 'translateY(10px)'
  userDropdown.style.pointerEvents = 'none'
  userDropdown.classList.remove('active')
  userDropdown.classList.remove('force-show')

  isDropdownOpen = false

  // 移除任何可能阻止悬停效果的内联样式
  userDropdown.style.position = ''
  userDropdown.style.left = ''
  userDropdown.style.top = ''

  // 确保相对定位正确
  userAvatar.style.position = 'relative'
  userAvatar.style.zIndex = '1001'

  // 用户头像点击事件
  userAvatar.addEventListener('click', function (e) {
    e.stopPropagation()
    toggleUserDropdown()
  })

  // 点击页面其他地方关闭用户下拉菜单
  document.addEventListener('click', function (e) {
    // 确保不是点击在用户菜单内部
    if (!userDropdown.contains(e.target) && e.target !== userAvatar) {
      toggleUserDropdown(false)
    }
  })

  // 额外添加悬停事件监听，确保在hover事件触发时正确显示
  userAvatar.addEventListener('mouseenter', function () {
    if (!isDropdownOpen) {
      userDropdown.style.opacity = '1'
      userDropdown.style.visibility = 'visible'
      userDropdown.style.transform = 'translateY(0)'
      userDropdown.style.pointerEvents = 'auto'
    }
  })

  userAvatar.addEventListener('mouseleave', function (e) {
    // 检查鼠标是否移到了下拉菜单上，如果不是，且没有点击激活，则隐藏菜单
    const rect = userDropdown.getBoundingClientRect()
    const isMouseInDropdown =
      e.clientX >= rect.left &&
      e.clientX <= rect.right &&
      e.clientY >= rect.top &&
      e.clientY <= rect.bottom

    if (!isMouseInDropdown && !isDropdownOpen) {
      userDropdown.style.opacity = '0'
      userDropdown.style.visibility = 'hidden'
      userDropdown.style.transform = 'translateY(10px)'
      userDropdown.style.pointerEvents = 'none'
    }
  })
}

// 新版通知系统JS
function optimizedInitNotifications() {
  const icon = document.getElementById('notificationIcon')
  const badge = document.getElementById('notificationBadge')
  const dropdown = document.getElementById('notificationDropdown')
  const list = document.getElementById('notificationList')
  const markAllReadBtn = document.getElementById('markAllReadBtn')

  if (!icon || !badge || !dropdown || !list || !markAllReadBtn) {
    console.error('Notification components not found!')
    return
  }

  let currentPage = 1
  let totalPages = 1
  let loading = false

  const iconMapping = {
    APPOINTMENT_NEW: 'fa-calendar-plus',
    APPOINTMENT_CONFIRMED: 'fa-calendar-check',
    APPOINTMENT_CANCELLED: 'fa-calendar-times',
    APPOINTMENT_COMPLETED: 'fa-check-circle',
    APPOINTMENT_REMINDER: 'fa-bell',
    REPORT_READY: 'fa-file-medical-alt',
    SYSTEM_ALERT: 'fa-exclamation-triangle',
    CHAT_MESSAGE: 'fa-comments',
    GENERAL: 'fa-info-circle',
  }

  function showSkeleton() {
    list.innerHTML = '<div class="notification-loading">加载中...</div>'
  }

  function renderNotifications(notifications, append = false) {
    if (!append && notifications.length === 0) {
      list.innerHTML = '<div class="notification-empty">暂无通知</div>'
      return
    }

    const html = notifications
      .map(
        n => `
            <div class="notification-item ${n.is_read ? '' : 'unread'}" data-id="${
          n.id
        }" data-url="${n.action_url || '#'}">
                <a href="${n.action_url || '#'}" class="notification-link">
                    <div class="icon-wrapper">
                        <i class="fas ${iconMapping[n.type] || 'fa-info-circle'}"></i>
                    </div>
                    <div class="notification-content">
                        <div class="notification-title">${n.title || '通知'}</div>
                        <div class="notification-message">${n.message || ''}</div>
                        <div class="notification-time">${n.created_at || ''}</div>
                    </div>
                </a>
            </div>
        `
      )
      .join('')

    if (append) {
      list.insertAdjacentHTML('beforeend', html)
    } else {
      list.innerHTML = html
    }
  }

  function updateBadge(count) {
    badge.textContent = count > 0 ? count : ''
    badge.style.display = count > 0 ? 'block' : 'none'
  }

  function loadNotifications(page = 1, append = false) {
    if (loading || page > totalPages) return
    loading = true
    if (!append) showSkeleton()

    fetch(`/api/notifications?page=${page}&limit=10`)
      .then(r => r.json())
      .then(data => {
        renderNotifications(data.notifications || [], append)
        updateBadge(data.unread_count || 0)
        currentPage = data.current_page
        totalPages = data.total_pages
      })
      .catch(err => {
        console.error('Failed to load notifications:', err)
        if (!append) list.innerHTML = '<div class="notification-empty">加载失败，请稍后重试</div>'
      })
      .finally(() => {
        loading = false
      })
  }

  function markAsRead(id, element) {
    fetch(`/api/notifications/${id}/read`, { method: 'POST' })
      .then(r => r.json())
      .then(data => {
        if (element) {
          element.classList.remove('unread')
        }
        updateBadge(data.unread_count || 0)
      })
  }

  // 事件委托处理通知点击
  list.addEventListener('click', function (e) {
    const item = e.target.closest('.notification-item')
    if (!item) return

    e.preventDefault()
    const id = item.dataset.id
    const url = item.dataset.url

    // 标记为已读
    if (item.classList.contains('unread')) {
      markAsRead(id, item)
    }

    // 处理跳转
    if (url && url !== '#') {
      const contentFrame = window.top.document.getElementById('content-frame')
      if (contentFrame) {
        dropdown.classList.remove('show')
        contentFrame.src = url
      } else {
        window.top.location.href = url
      }
    }
  })

  markAllReadBtn.onclick = function () {
    fetch('/api/notifications/read-all', { method: 'POST' }).then(() => {
      list.querySelectorAll('.notification-item.unread').forEach(item => {
        item.classList.remove('unread')
      })
      updateBadge(0)
    })
  }

  icon.onclick = function (e) {
    e.stopPropagation()
    const isVisible = dropdown.classList.toggle('show')
    if (isVisible) {
      currentPage = 1
      totalPages = 1 // 重置以便重新加载
      loadNotifications(1, false)
    }
  }

  list.onscroll = function () {
    if (list.scrollTop + list.clientHeight >= list.scrollHeight - 50 && !loading) {
      if (currentPage < totalPages) {
        loadNotifications(currentPage + 1, true)
      }
    }
  }

  function pollUnreadCount() {
    fetch('/api/notifications/count')
      .then(r => r.json())
      .then(data => updateBadge(data.total_unread || 0))
  }

  // 初始加载 & 定时轮询
  pollUnreadCount()
  setInterval(pollUnreadCount, 60000) // 1分钟轮询一次
}

// 修复顶部导航栏用户菜单
function fixTopNavUserMenu() {
  const userAvatar = document.getElementById('userAvatar')
  const userDropdown = document.getElementById('userDropdown')

  if (!userAvatar || !userDropdown) {
    console.warn('顶部用户菜单元素未找到')
    return
  }

  // 确保菜单具有正确的初始样式
  userDropdown.style.display = 'none'
  userDropdown.style.visibility = 'hidden'
  userDropdown.style.opacity = '0'

  // 绑定事件处理
  userAvatar.addEventListener('mouseenter', function () {
    userDropdown.style.display = 'block'
    userDropdown.style.visibility = 'visible'
    userDropdown.style.opacity = '1'
    userDropdown.style.transform = 'translateY(0)'
  })

  userAvatar.addEventListener('mouseleave', function (e) {
    // 检查鼠标是否移入下拉菜单
    const rect = userDropdown.getBoundingClientRect()
    if (
      !(
        e.clientX >= rect.left &&
        e.clientX <= rect.right &&
        e.clientY >= rect.top &&
        e.clientY <= rect.bottom
      )
    ) {
      // 设置短暂延迟，允许鼠标移入菜单
      setTimeout(function () {
        // 确保鼠标没有在菜单上才隐藏
        if (!userDropdown.matches(':hover')) {
          userDropdown.style.display = 'none'
          userDropdown.style.visibility = 'hidden'
          userDropdown.style.opacity = '0'
        }
      }, 100)
    }
  })

  userDropdown.addEventListener('mouseleave', function () {
    userDropdown.style.display = 'none'
    userDropdown.style.visibility = 'hidden'
    userDropdown.style.opacity = '0'
  })

  // 确保用户菜单在iframe页面加载时保持正确的z-index
  const contentFrame = document.getElementById('content-frame')
  if (contentFrame) {
    contentFrame.addEventListener('load', function () {
      userAvatar.style.zIndex = '19999'
      userDropdown.style.zIndex = '20000'
    })
  }
}

// 页面预加载函数 - 通过Link Prefetching提高页面加载速度
function prefetchPage(url) {
  // 检查是否已经存在同一个预加载链接
  const existingPrefetch = document.querySelector(`link[rel="prefetch"][href="${url}"]`)
  if (existingPrefetch) return

  // 创建预加载链接元素
  const prefetch = document.createElement('link')
  prefetch.rel = 'prefetch'
  prefetch.href = url

  // 添加到文档头部
  document.head.appendChild(prefetch)

  // 创建DNS预解析链接
  const preconnect = document.createElement('link')
  preconnect.rel = 'preconnect'
  preconnect.href = new URL(url, window.location.href).origin

  // 添加到文档头部
  document.head.appendChild(preconnect)
}

function showGlobalSkeleton() {
  let skeleton = document.querySelector('.global-skeleton')
  if (!skeleton) {
    skeleton = document.createElement('div')
    skeleton.className = 'global-skeleton'
    skeleton.innerHTML = `
            <div class="skeleton-header"></div>
            <div class="skeleton-block"></div>
            <div class="skeleton-block"></div>
            <div class="skeleton-block"></div>
        `
    document.querySelector('.main-content').appendChild(skeleton)
  }
  skeleton.style.display = ''
}

function hideGlobalSkeleton() {
  const skeleton = document.querySelector('.global-skeleton')
  if (skeleton) skeleton.style.display = 'none'
}

// 点击页面其他地方时自动隐藏通知下拉菜单
window.addEventListener('click', function (event) {
  const icon = document.getElementById('notificationIcon')
  const dropdown = document.getElementById('notificationDropdown')
  if (dropdown && !icon.contains(event.target) && !dropdown.contains(event.target)) {
    dropdown.classList.remove('show')
  }
})
