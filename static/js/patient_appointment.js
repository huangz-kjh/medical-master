/**
 * 优化后的患者预约管理JavaScript
 * 切换标签页和分页时，使用统一的局部模糊加载动画
 */
document.addEventListener('DOMContentLoaded', function () {
  // --- 预加载相关 ---
  const preloadCache = new Set()
  /**
   * 预加载URL，利用浏览器缓存。
   * @param {string} url - 要预加载的URL
   */
  function preloadUrl(url) {
    if (!preloadCache.has(url)) {
      // 只管发出请求，浏览器会自动处理缓存，无需处理响应
      fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
      preloadCache.add(url)
    }
  }

  const contentWrapper = document.querySelector('.list-content-wrapper')
  const tabsContainer = document.querySelector('.tabs')
  const bookButton = document.getElementById('book-appointment-btn')

  if (!contentWrapper) {
    console.error('关键元素 .list-content-wrapper 未找到，脚本无法初始化。')
    return
  }

  // 明确地为"新建预约"按钮绑定事件
  if (bookButton) {
    bookButton.addEventListener('click', function (e) {
      e.preventDefault()
      e.stopPropagation()
      showNewAppointmentModal()
    })
  } else {
    console.error('无法找到 #book-appointment-btn 按钮。')
  }

  // --- 使用事件委托处理所有动态内容点击 ---
  document.body.addEventListener('click', function (e) {
    // 1. 处理标签页和分页链接
    const link = e.target.closest('.tabs a.tab-item, .pagination a')
    if (link && !link.classList.contains('active')) {
      e.preventDefault()
      e.stopPropagation()

      const url = new URL(link.getAttribute('href'), window.location.origin)

      // 关键修复：当点击的是标签页(tab-item)时，必须手动附加分页参数
      if (link.classList.contains('tab-item')) {
        // 读取当前选择的每页显示数量
        const perPageSelect = document.getElementById('perPageSelect')
        const perPage = perPageSelect ? perPageSelect.value : '10' // 默认10

        // 将"每页数量"和"页码=1"附加到URL上
        url.searchParams.set('per_page', perPage)
        url.searchParams.set('page', '1') // 切换标签页时，总是回到第一页
      }

      // 对于分页链接，其href已经包含了所有正确的参数，因此无需额外处理

      if (url) {
        loadContent(url.toString(), true)
      }
      return // 处理完毕，退出
    }

    // 2. 处理"详情"按钮
    const detailButton = e.target.closest('button.btn-detail')
    if (detailButton) {
      e.preventDefault()
      e.stopPropagation()
      viewAppointmentDetails(detailButton.dataset.id)
      return // 处理完毕，退出
    }

    // 3. 处理"取消"按钮
    const cancelButton = e.target.closest('button.btn-cancel')
    if (cancelButton) {
      e.preventDefault()
      e.stopPropagation()
      confirmCancelAppointment(cancelButton.dataset.id)
      return // 处理完毕，退出
    }

    // 4. 处理所有模态框的关闭按钮
    const closeButton = e.target.closest('.modal-close, #closeDetailsBtn, #abortCancelBtn')
    if (closeButton) {
      e.preventDefault()
      e.stopPropagation()
      const modal = closeButton.closest('.modal-overlay')
      if (modal) {
        modal.classList.remove('show')
      }
      return // 处理完毕，退出
    }

    // 5. 处理确认取消
    const confirmCancel = e.target.closest('#confirmCancelBtn')
    if (confirmCancel) {
      e.preventDefault()
      e.stopPropagation()
      const modal = confirmCancel.closest('#cancelAppointmentModal')
      if (modal) {
        cancelAppointment(
          modal.querySelector('#cancelAppointmentId').value,
          modal.querySelector('#cancelReason').value
        )
      }
      return
    }

    // 6. 处理提交新预约
    const submitNewAppt = e.target.closest('#submitAppointment')
    if (submitNewAppt) {
      e.preventDefault()
      e.stopPropagation()
      submitNewAppointment()
      return
    }
  })

  // --- 新增：事件委托，鼠标悬停预加载 ---
  document.body.addEventListener('mouseover', function (e) {
    const link = e.target.closest('.tabs a.tab-item, .pagination a')
    if (link && !link.classList.contains('active')) {
      const url = link.getAttribute('href')
      if (url) {
        preloadUrl(url)
      }
    }
  })

  // --- 事件监听：每页数量选择器 ---
  document.body.addEventListener('change', function (e) {
    if (e.target && e.target.id === 'perPageSelect') {
      const perPage = e.target.value
      // 从当前激活的Tab获取基础URL
      const activeTab = tabsContainer?.querySelector('a.tab-item.active')
      const baseUrl = activeTab ? activeTab.getAttribute('href') : window.location.pathname
      const currentUrl = new URL(baseUrl, window.location.origin)

      currentUrl.searchParams.set('page', '1') // 切换每页数量时，重置到第一页
      currentUrl.searchParams.set('per_page', perPage)
      loadContent(currentUrl.toString(), true)
    }
  })

  /**
   * 将HTML内容更新到DOM，并处理URL和标签页状态
   * @param {string} html - 要注入的HTML字符串
   * @param {string} url - 对应的URL，用于更新浏览器历史
   */
  function updateContent(html, url) {
    const contentWrapper = document.querySelector('.list-content-wrapper')
    if (contentWrapper) {
      contentWrapper.innerHTML = html
      // 添加动画class来触发淡入效果
      contentWrapper.classList.add('content-fade-in')
      // 动画结束后移除class，以便下次还能触发
      contentWrapper.addEventListener(
        'animationend',
        () => {
          contentWrapper.classList.remove('content-fade-in')
        },
        { once: true }
      )
    }
    history.pushState({}, '', url)

    const urlParams = new URLSearchParams(new URL(url, window.location.origin).search)
    const status_group = urlParams.get('status_group') || 'active'
    document.querySelectorAll('.tabs .tab-item').forEach(tab => {
      tab.classList.remove('active')
      if (tab.getAttribute('href').includes(`status_group=${status_group}`)) {
        tab.classList.add('active')
      }
    })
  }

  /**
   * 从服务器加载内容
   * @param {string} url - 要请求的URL
   * @param {boolean} showLoader - 是否显示加载动画
   */
  function loadContent(url, showLoader = false) {
    if (showLoader) showLoading()

    // 创建两个Promise：一个用于数据请求，一个用于保证最小加载时间
    const fetchPromise = fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } }).then(
      response => {
        if (!response.ok) throw new Error('网络请求失败')
        return response.text()
      }
    )

    // 保证加载动画至少显示150毫秒，减少感知延迟，但足以防止闪烁
    const timerPromise = new Promise(resolve => setTimeout(resolve, 150))

    // 等待数据和最短时间都完成后再更新UI
    Promise.all([fetchPromise, timerPromise])
      .then(([html]) => {
        updateContent(html, url)
      })
      .catch(err => {
        showNotification(err.message, 'error')
        // 即使出错也要隐藏动画
        if (showLoader) hideLoading()
      })
      .finally(() => {
        // 在Promise.all之后才隐藏动画
        if (showLoader) hideLoading()
      })
  }

  // --- 以下是功能函数 ---

  function showLoading() {
    document.querySelector('.appointment-list')?.classList.add('loading')
  }

  function hideLoading() {
    document.querySelector('.appointment-list')?.classList.remove('loading')
  }

  function showNotification(message, type = 'success') {
    const popup = document.getElementById('notification-popup')
    if (!popup) return
    popup.textContent = message
    popup.className = `notification notification-${type} show`
    setTimeout(() => popup.classList.remove('show'), 3000)
  }

  function closeAllModals() {
    document.querySelectorAll('.modal-overlay').forEach(modal => modal.classList.remove('show'))
  }

  function viewAppointmentDetails(appointmentId) {
    if (!appointmentId) return
    // 对于API调用，我们可以选择使用一个不同的、全局的加载指示器
    // 但为了保持一致性，此处暂时也使用局部加载动画
    showLoading()
    fetch(`/api/appointments/${appointmentId}/details`)
      .then(response => (response.ok ? response.json() : Promise.reject('网络请求失败')))
      .then(data => {
        if (data.status === 'success' && data.data) {
          displayAppointmentDetails(data.data)
        } else {
          throw new Error(data.message || '无法获取详情')
        }
      })
      .catch(err => showNotification(err.message, 'error'))
      .finally(hideLoading)
  }

  function displayAppointmentDetails(appt) {
    const modal = document.getElementById('appointmentDetailsModal')
    if (!modal) return
    modal.querySelector('#detailId').textContent = appt.code || appt.appointment_id || 'N/A'
    modal.querySelector('#detailType').textContent = appt.appointment_type?.display_name || 'N/A'
    modal.querySelector('#detailDepartment').textContent = appt.department?.display_name || 'N/A'
    modal.querySelector('#detailDoctor').textContent = appt.doctor_name || '未知医生'
    modal.querySelector('#detailDate').textContent = appt.appointment_date || 'N/A'
    modal.querySelector('#detailTime').textContent = appt.time_slot?.display_name || 'N/A'
    modal.querySelector('#detailStatus').textContent = appt.status?.display_name || 'N/A'
    modal.querySelector('#detailSymptoms').textContent = appt.symptoms || '无'
    modal.querySelector('#detailNotes').textContent = appt.notes || '无'
    modal.classList.add('show')
  }

  function confirmCancelAppointment(appointmentId) {
    const modal = document.getElementById('cancelAppointmentModal')
    if (modal) {
      modal.querySelector('#cancelAppointmentId').value = appointmentId
      modal.classList.add('show')
    }
  }

  function cancelAppointment(appointmentId, reason) {
    if (!appointmentId) return
    showLoading()

    // 使用JSON格式发送数据，而不是FormData
    const body = JSON.stringify({ reason: reason || '' })

    fetch(`/api/appointments/${appointmentId}/cancel`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: body,
    })
      .then(response => response.json())
      .then(data => {
        if (data.status === 'success') {
          showNotification('预约已取消', 'success')
          closeAllModals()
          // Instead of reloading the whole page, load the current active tab
          const activeTab = document.querySelector('.tabs .tab-item.active')
          const urlToLoad = activeTab ? activeTab.href : window.location.href
          loadContent(urlToLoad, true)
        } else {
          throw new Error(data.message || '取消失败')
        }
      })
      .catch(err => showNotification(err.message, 'error'))
      .finally(hideLoading)
  }

  function showNewAppointmentModal() {
    const modal = document.getElementById('book-appointment-modal')
    if (modal) {
      modal.querySelector('form')?.reset()
      loadAllDoctors('doctorSelect')

      // 设置日期选择范围：今天到一周后
      const dateInput = modal.querySelector('#appointmentDate')
      if (dateInput) {
        const today = new Date()
        const nextWeek = new Date()
        nextWeek.setDate(today.getDate() + 7)

        // 格式化日期为YYYY-MM-DD
        const formatDate = date => {
          const year = date.getFullYear()
          const month = String(date.getMonth() + 1).padStart(2, '0')
          const day = String(date.getDate()).padStart(2, '0')
          return `${year}-${month}-${day}`
        }

        // 设置最小和最大日期
        dateInput.min = formatDate(today)
        dateInput.max = formatDate(nextWeek)
        dateInput.value = formatDate(today)
      }

      modal.classList.add('show')
    }
  }

  function loadAllDoctors(selectId) {
    const doctorSelect = document.getElementById(selectId)
    if (!doctorSelect) return

    fetch('/api/v2/doctors')
      .then(response => {
        if (!response.ok) {
          throw new Error('网络错误，无法加载医生列表')
        }
        return response.json()
      })
      .then(data => {
        if (data.status === 'success') {
          doctorSelect.innerHTML = '<option value="">请选择</option>'
          if (data.data && data.data.length > 0) {
            data.data.forEach(doctor => {
              const option = document.createElement('option')
              option.value = doctor.id
              option.textContent = doctor.name
              doctorSelect.appendChild(option)
            })
          } else {
            doctorSelect.innerHTML = '<option value="">暂无可预约医生</option>'
          }
        } else {
          throw new Error(data.message || '加载医生列表失败')
        }
      })
      .catch(err => {
        showNotification(err.message, 'error')
        doctorSelect.innerHTML = '<option value="">加载失败，请重试</option>'
      })
  }

  function submitNewAppointment() {
    const form = document.getElementById('book-appointment-form')
    if (!form) return

    const formData = new FormData(form)
    const data = Object.fromEntries(formData.entries())

    if (
      !data.doctor_id ||
      !data.date ||
      !data.time_slot ||
      !data.appointment_type ||
      !data.department
    ) {
      showNotification('请填写所有必填项', 'error')
      return
    }

    showLoading()
    fetch('/api/appointments', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify(data),
    })
      .then(response => {
        return response.json()
      })
      .then(data => {
        if (data.status === 'success') {
          showNotification('预约成功！', 'success')
          closeAllModals()
          // Go to the 'active' tab to show the newly created appointment
          const activeTabUrl = document.querySelector(
            "a.tab-item[href*='status_group=active']"
          ).href
          loadContent(activeTabUrl, true)
        } else {
          throw new Error(data.message || '预约失败')
        }
      })
      .catch(err => {
        showNotification(err.message, 'error')
      })
      .finally(hideLoading)
  }
})
