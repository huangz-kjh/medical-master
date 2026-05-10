// dashboard.js - 优化版
document.addEventListener('DOMContentLoaded', function () {
  const role = window.currentUserRole
  const fetchStats = () => fetch('/api/dashboard/stats').then(res => res.json())
  const fetchActivity = () => fetch('/api/dashboard/recent-activity').then(res => res.json())
  const fetchCharts = () => fetch('/api/dashboard/charts').then(res => res.json())
  const fetchHealthData = () => fetch('/api/dashboard/health-data').then(res => res.json())

  // 显示当前日期
  const currentDateElement = document.getElementById('currentDate')
  if (currentDateElement) {
    const options = { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' }
    currentDateElement.textContent = new Date().toLocaleDateString('zh-CN', options)
  }

  if (!role) {
    renderError('top-row-container', '无法确定用户角色，加载失败')
    return
  }

  // 获取顶部数据和活动
  Promise.all([fetchStats(), fetchActivity()])
    .then(([statsRes, activityRes]) => {
      // 渲染顶部行
      if (statsRes.status === 'success') {
        renderTopRow(statsRes.data, activityRes.data, role)
      } else {
        renderError('top-row-container', '无法加载统计数据')
      }

      // 如果是患者角色，延迟加载健康数据
      if (role === 'patient') {
        // 使用IntersectionObserver检测健康数据容器是否进入视口
        const healthDataContainer = document.getElementById('health-data-container')
        if (healthDataContainer) {
          const observer = new IntersectionObserver(
            entries => {
              entries.forEach(entry => {
                if (entry.isIntersecting) {
                  // 当容器进入视口时，加载健康数据
                  loadHealthData()
                  // 停止观察
                  observer.unobserve(entry.target)
                }
              })
            },
            {
              threshold: 0.1, // 当10%的容器可见时触发
            }
          )

          observer.observe(healthDataContainer)

          // 添加一个占位符
          healthDataContainer.innerHTML = `
            <div class="data-card">
              <div class="data-header"><div class="data-title">加载中...</div></div>
              <div class="data-content">
                <div class="skeleton-loader" style="width: 100%; height: 200px"></div>
              </div>
            </div>
          `
        }
      }
    })
    .catch(error => {
      console.error('仪表板数据加载失败:', error)
      renderError('top-row-container', '网络错误，加载失败')
    })

  // 异步加载图表数据
  fetchCharts()
    .then(chartsRes => {
      if (chartsRes.status === 'success') {
        renderCharts(chartsRes.data, role)
      } else {
        renderError('charts-section', '无法加载图表数据')
      }
    })
    .catch(error => {
      console.error('图表数据加载失败:', error)
      renderError('charts-section', '网络错误，加载失败')
    })

  function loadHealthData() {
    fetchHealthData()
      .then(response => {
        if (response.status === 'success') {
          renderPatientHealthData(response.data)
        } else {
          renderError('health-data-container', '无法加载健康数据')
        }
      })
      .catch(error => {
        console.error('健康数据加载失败:', error)
        renderError('health-data-container', '网络错误，加载失败')
      })
  }

  function renderTopRow(stats, activity, role) {
    const container = document.getElementById('top-row-container')
    if (!container) return

    let html = ''

    if (role === 'doctor') {
      html = `
        <div class="stat-card"><h3>我的患者</h3><div class="stat-value">${
          stats.my_patients || 0
        }</div></div>
        <div class="stat-card"><h3>待确认预约</h3><div class="stat-value">${
          stats.pending_appointments || 0
        }</div></div>
        <div class="stat-card"><h3>未读通知</h3><div class="stat-value">${
          stats.unread_notifications || 0
        }</div></div>
        <div class="stat-card"><h3>今日预约</h3><div class="stat-value">${
          stats.today_appointments_count || 0
        }</div></div>
      `
      // For doctor, recent activity can be in a separate row if needed in future
    } else if (role === 'patient') {
      // Stat cards
      html += `
        <div class="stat-card">
          <h3>待处理预约</h3>
          <div class="stat-value">${stats.pending_appointments || 0} 条</div>
        </div>
        <div class="stat-card">
          <h3>未读消息</h3>
          <div class="stat-value">${stats.unread_notifications || 0} 条</div>
        </div>
      `

      // Recent activity card
      html += '<div class="stat-card recent-activity-card">'
      if (activity && activity.length > 0) {
        const item = activity[0]
        const time = item.timestamp
          ? new Date(item.timestamp)
              .toLocaleString('zh-CN', {
                year: '2-digit',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
              })
              .replace(/\//g, '-')
          : '未知时间'
        let text = ''
        let icon = '<i class="fas fa-bell"></i>'

        if (item.type === 'appointment') {
          icon = '<i class="fas fa-calendar-check"></i>'
          text = `您与 <strong>${item.doctor_name || '未知医生'}</strong> 的预约已 <strong>${
            item.status_display || '未知'
          }</strong>`
        } else if (item.type === 'report') {
          icon = '<i class="fas fa-file-medical"></i>'
          text = `新的影像报告 <strong>"${item.report_title || '无标题'}"</strong> 已出`
        }

        html += `
          <div class="activity-item">
            <div class="activity-icon">${icon}</div>
            <div class="activity-details">
              <div class="activity-main">${text}</div>
              <div class="activity-date">${time}</div>
            </div>
          </div>
        `
      } else {
        html += '<div class="no-data">暂无最近动态</div>'
      }
      html += '</div>'
    }

    container.innerHTML = html
  }

  function renderPatientHealthData(data) {
    const healthDataContainer = document.getElementById('health-data-container')
    if (!healthDataContainer) return

    let healthDataHtml = ''

    // 1. 下次预约卡片 - 标准大小
    healthDataHtml += `
      <div class="data-card">
        <div class="data-header"><div class="data-title">下次预约</div></div>
        <div class="data-content">
    `

    if (data.next_appointment) {
      healthDataHtml += `
        <div class="health-data-item">
          <div class="health-data-label">预约日期</div>
          <div class="health-data-value">${data.next_appointment.date}</div>
        </div>
        <div class="health-data-item">
          <div class="health-data-label">就诊医生</div>
          <div class="health-data-value">${data.next_appointment.doctor}</div>
        </div>
        <div class="health-data-item">
          <div class="health-data-label">就诊科室</div>
          <div class="health-data-value">${data.next_appointment.department}</div>
        </div>
        <div class="health-data-item">
          <div class="health-data-label">时间段</div>
          <div class="health-data-value">${data.next_appointment.time_slot}</div>
        </div>
      `
    } else {
      healthDataHtml += `<div class="no-data">暂无已确认的预约</div>`
    }

    healthDataHtml += `</div></div>`

    // 2. 当前用药记录卡片
    healthDataHtml += `
      <div class="data-card">
        <div class="data-header"><div class="data-title">当前用药</div></div>
        <div class="data-content">
    `

    if (data.latest_medication) {
      healthDataHtml += `
        <div class="health-data-item">
          <div class="health-data-label">药物名称</div>
          <div class="health-data-value">${data.latest_medication.name || '未记录'}</div>
        </div>
        <div class="health-data-item">
          <div class="health-data-label">剂量</div>
          <div class="health-data-value">${data.latest_medication.dosage || '未记录'}</div>
        </div>
        <div class="health-data-item">
          <div class="health-data-label">用药频率</div>
          <div class="health-data-value">${data.latest_medication.frequency || '未记录'}</div>
        </div>
        <div class="health-data-item">
          <div class="health-data-label">开始日期</div>
          <div class="health-data-value">${data.latest_medication.start_date}</div>
        </div>
      `
    } else {
      healthDataHtml += `<div class="no-data">暂无用药记录</div>`
    }

    healthDataHtml += `</div></div>`

    // 3. 体检数据图表卡片
    healthDataHtml += `
      <div class="data-card chart-card">
        <div class="data-header"><div class="data-title">体检数据</div></div>
        <div class="data-content" id="physical-exam-chart" style="height: 300px; width: 100%;">
    `

    if (data.latest_exam) {
      healthDataHtml += `<div class="skeleton-loader" style="width: 100%; height: 300px"></div>`
    } else {
      healthDataHtml += `<div class="no-data">暂无体检数据</div>`
    }

    healthDataHtml += `</div></div>`

    // 4. 神经功能评估图表卡片
    healthDataHtml += `
      <div class="data-card chart-card">
        <div class="data-header"><div class="data-title">神经功能评估</div></div>
        <div class="data-content" id="neuro-assessment-chart" style="height: 300px; width: 100%;">
    `

    if (data.latest_assessment) {
      healthDataHtml += `<div class="skeleton-loader" style="width: 100%; height: 300px"></div>`
    } else {
      healthDataHtml += `<div class="no-data">暂无神经功能评估数据</div>`
    }

    healthDataHtml += `</div></div>`

    healthDataContainer.innerHTML = healthDataHtml

    // 初始化体检数据图表
    if (data.latest_exam) {
      setTimeout(() => {
        const chartDom = document.getElementById('physical-exam-chart')
        if (chartDom) {
          const chart = window.echarts.init(chartDom)
          chart.setOption({
            tooltip: {
              trigger: 'axis',
              axisPointer: {
                type: 'shadow',
              },
            },
            grid: {
              left: '3%',
              right: '8%',
              bottom: '10%',
              top: '15%',
              containLabel: true,
            },
            xAxis: {
              type: 'category',
              data: ['心率', '收缩压', '舒张压', '体温'],
              axisLabel: {
                interval: 0,
                rotate: 0,
              },
            },
            yAxis: [
              {
                type: 'value',
                name: '数值',
              },
            ],
            series: [
              {
                name: '体检数据',
                type: 'bar',
                barWidth: '40%',
                data: [
                  {
                    value: data.latest_exam.heart_rate || 0,
                    itemStyle: { color: '#5470c6' },
                  },
                  {
                    value: data.latest_exam.blood_pressure
                      ? parseInt(data.latest_exam.blood_pressure.split('/')[0])
                      : 0,
                    itemStyle: { color: '#91cc75' },
                  },
                  {
                    value: data.latest_exam.blood_pressure
                      ? parseInt(data.latest_exam.blood_pressure.split('/')[1])
                      : 0,
                    itemStyle: { color: '#fac858' },
                  },
                  {
                    value: data.latest_exam.temperature || 0,
                    itemStyle: { color: '#ee6666' },
                  },
                ],
              },
            ],
          })

          // 窗口大小变化时重绘图表
          window.addEventListener('resize', () => chart.resize())
        }
      }, 10)
    }

    // 初始化神经评估图表
    if (data.latest_assessment) {
      setTimeout(() => {
        const chartDom = document.getElementById('neuro-assessment-chart')
        if (chartDom) {
          const chart = window.echarts.init(chartDom)
          chart.setOption({
            tooltip: {
              trigger: 'axis',
              axisPointer: {
                type: 'shadow',
              },
            },
            grid: {
              left: '3%',
              right: '8%',
              bottom: '10%',
              top: '15%',
              containLabel: true,
            },
            xAxis: {
              type: 'category',
              data: ['MMSE评分', 'MOCA评分', 'GCS评分'],
              axisLabel: {
                interval: 0,
                rotate: 0,
              },
            },
            yAxis: [
              {
                type: 'value',
                name: '分数',
                max: 30,
              },
            ],
            series: [
              {
                name: '神经评估',
                type: 'bar',
                barWidth: '40%',
                data: [
                  {
                    value: data.latest_assessment.mmse_score || 0,
                    itemStyle: { color: '#5470c6' },
                  },
                  {
                    value: data.latest_assessment.moca_score || 0,
                    itemStyle: { color: '#91cc75' },
                  },
                  {
                    value: data.latest_assessment.gcs_score || 0,
                    itemStyle: { color: '#fac858' },
                  },
                ],
              },
            ],
          })

          // 窗口大小变化时重绘图表
          window.addEventListener('resize', () => chart.resize())
        }
      }, 10)
    }
  }

  function renderCharts(data, role) {
    const chartsSection = document.querySelector('.charts-section')
    if (!chartsSection) return
    chartsSection.innerHTML = ''

    if (role === 'doctor') {
      chartsSection.style.gridTemplateColumns = '1fr 1fr'
      chartsSection.innerHTML = `
                <div class="data-card chart-card">
                    <div class="data-header"><div class="data-title">患者状态分布</div></div>
                    <div class="data-content" id="patient-status-chart" style="height: 280px;"></div>
                </div>
                <div class="data-card chart-card">
                    <div class="data-header"><div class="data-title">预约类型分布</div></div>
                    <div class="data-content" id="appointment-types-chart" style="height: 280px;"></div>
                </div>
            `
      if (data.patient_status && data.patient_status.length > 0) {
        initPieChart('patient-status-chart', '患者状态分布', data.patient_status)
      } else {
        renderErrorInContainer('patient-status-chart', '无患者状态数据')
      }
      if (data.appointment_types && data.appointment_types.length > 0) {
        initPieChart('appointment-types-chart', '预约类型分布', data.appointment_types)
      } else {
        renderErrorInContainer('appointment-types-chart', '无预约类型数据')
      }
    } else if (role === 'patient') {
      chartsSection.style.gridTemplateColumns = '1fr'
      chartsSection.innerHTML = `
                <div class="data-card chart-card">
                    <div class="data-header"><div class="data-title">我的预约状态分布</div></div>
                    <div class="data-content" id="patient-appointment-chart" style="height: 280px;"></div>
                </div>
            `

      if (data.appointment_status && data.appointment_status.length > 0) {
        initPieChart('patient-appointment-chart', '我的预约状态', data.appointment_status, true)
      } else {
        renderErrorInContainer('patient-appointment-chart', '无预约数据')
      }
    }
  }

  function initPieChart(elementId, name, data, isDonut = false) {
    const chartDom = document.getElementById(elementId)
    if (!chartDom) return

    try {
      // 检查echarts是否可用
      if (typeof window.echarts === 'undefined') {
        console.error('ECharts未定义，无法创建图表')
        return
      }

      const chart = window.echarts.init(chartDom)
      chart.setOption({
        tooltip: { trigger: 'item' },
        legend: { top: 'bottom', left: 'center', type: 'scroll' },
        series: [
          {
            name: name,
            type: 'pie',
            radius: isDonut ? ['45%', '65%'] : '60%',
            avoidLabelOverlap: false,
            label: { show: !isDonut, position: 'outside' },
            emphasis: { label: { show: isDonut, fontSize: '18', fontWeight: 'bold' } },
            labelLine: { show: !isDonut },
            data: data,
          },
        ],
      })

      // 确保图表正确渲染
      window.addEventListener('resize', function () {
        chart.resize()
      })
    } catch (error) {
      console.error(`初始化图表 ${elementId} 失败:`, error)
    }
  }

  function renderError(containerId, message) {
    const container = document.getElementById(containerId)
    if (container) {
      container.innerHTML = `<div class="error-state">${message}</div>`
    }
  }
  function renderErrorInContainer(containerId, message) {
    const container = document.getElementById(containerId)
    if (container) {
      container.innerHTML = `<div class="no-data"><p>${message}</p></div>`
    }
  }

  // DOM加载完成后，确保所有图表正确渲染
  window.addEventListener('load', function () {
    setTimeout(function () {
      window.dispatchEvent(new Event('resize'))
    }, 300)
  })
})
