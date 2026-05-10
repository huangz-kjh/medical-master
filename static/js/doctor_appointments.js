// 医生预约管理页面JS - 修复版
function initPage() {
  layui.use(['form', 'layer', 'element', 'laydate'], function () {
    const form = layui.form
    const layer = layui.layer
    const element = layui.element
    const laydate = layui.laydate
    const $ = layui.jquery

    var currentTab = 'all' // all, pending, confirmed
    var currentSearch = {
      q: '',
      status: '',
      date_range: '',
    }

    // 渲染日期范围选择器
    laydate.render({
      elem: '#dateRangeFilter',
      range: true,
    })

    /**
     * 加载预约列表的核心函数
     * @param {string} tabKey - 当前的tab (all, pending, confirmed)
     * @param {number} page - 请求的页码
     * @param {object} searchParams - 搜索参数
     */
    function loadAppointments(tabKey, page, searchParams) {
      var status = ''
      if (tabKey === 'pending') status = 'pending'
      if (tabKey === 'confirmed') status = 'confirmed'

      var params = {
        page: page || 1,
        limit: 10,
        status: searchParams.status || status, // 搜索筛选优先于tab状态
        q: searchParams.q || '',
        date_range: searchParams.date_range || '',
      }

      var $tableBody = $('#' + tabKey + 'TableBody')
      var $paginationContainer = $('#' + tabKey + 'Pagination')

      // 清空并显示骨架屏
      var skeletonHtml = ''
      for (var i = 0; i < 5; i++) {
        skeletonHtml +=
          '<tr>' +
          '<td><div class="skeleton-loader" style="width:80px;"></div></td>' +
          '<td><div class="skeleton-loader" style="width:60px;"></div></td>' +
          '<td><div class="skeleton-loader" style="width:100px;"></div></td>' +
          '<td><div class="skeleton-loader" style="width:70px;"></div></td>' +
          '<td><div class="skeleton-loader" style="width:50px;"></div></td>' +
          '<td><div class="skeleton-loader" style="width:120px;"></div></td>' +
          '<td><div class="skeleton-loader" style="width:100px;"></div></td>' +
          '</tr>'
      }
      $tableBody.html(skeletonHtml)

      $.ajax({
        url: '/api/appointments/doctor-paginated',
        type: 'GET',
        data: params,
        success: function (res) {
          if (res.status === 'success') {
            renderTable(tabKey, res.data)
            renderPagination(
              tabKey,
              page,
              res.pagination.total_pages,
              res.pagination.total_items,
              searchParams
            )
          } else {
            layer.msg(res.message || '加载失败', { icon: 2 })
            $tableBody.html(
              '<tr><td colspan="7" style="text-align: center;">加载数据失败...</td></tr>'
            )
          }
        },
        error: function () {
          layer.msg('网络错误，加载预约列表失败', { icon: 2 })
          $tableBody.html(
            '<tr><td colspan="7" style="text-align: center;">加载数据失败...</td></tr>'
          )
        },
      })
    }

    /**
     * 渲染表格数据
     * @param {string} tabKey - 目标tab
     * @param {Array} data - 预约数据
     */
    function renderTable(tabKey, data) {
      var $tableBody = $('#' + tabKey + 'TableBody')
      if (!data || data.length === 0) {
        $tableBody.html(
          '<tr><td colspan="7" style="text-align: center; padding: 20px;">没有找到相关预约</td></tr>'
        )
        return
      }

      var html = ''
      data.forEach(function (appt) {
        var statusBadge = getStatusBadge(appt.status.value)
        html += `
                    <tr>
                        <td>${appt.patient_name || '未知'}</td>
                        <td>${
                          (appt.appointment_type && appt.appointment_type.display_name) || '未知'
                        }</td>
                        <td>${appt.appointment_date || '未知'}</td>
                        <td>${(appt.time_slot && appt.time_slot.display_name) || '未知'}</td>
                        <td>${statusBadge}</td>
                        <td>${appt.created_at || '未知'}</td>
                        <td>
                            <button class="layui-btn layui-btn-xs" onclick="viewAppointmentDetail(${
                              appt.appointment_id
                            })">详情</button>
                            ${getActions(appt)}
                                    </td>
                    </tr>
                `
      })
      $tableBody.html(html)
    }

    /**
     * 根据状态获取徽章HTML
     */
    function getStatusBadge(status) {
      var statusMap = {
        pending: { text: '待确认', class: 'layui-bg-orange' },
        confirmed: { text: '已确认', class: 'layui-bg-green' },
        completed: { text: '已完成', class: '' },
        cancelled: { text: '已取消', class: 'layui-bg-gray' },
        rejected: { text: '已拒绝', class: 'layui-bg-red' },
      }
      var info = statusMap[status] || { text: status || '未知', class: 'layui-bg-gray' }
      return `<span class="layui-badge ${info.class}">${info.text}</span>`
    }

    /**
     * 根据状态获取操作按钮HTML
     */
    function getActions(appt) {
      if (appt.status && appt.status.value === 'pending') {
        return `
                    <button class="layui-btn layui-btn-normal layui-btn-xs" onclick="confirmAppointment(${appt.appointment_id})">确认</button>
                    <button class="layui-btn layui-btn-danger layui-btn-xs" onclick="rejectAppointment(${appt.appointment_id})">拒绝</button>
                `
      }
      if (appt.status && appt.status.value === 'confirmed') {
        return `<button class="layui-btn layui-btn-warm layui-btn-xs" onclick="completeAppointment(${appt.appointment_id})">完成</button>`
      }
      return ''
    }

    /**
     * 渲染分页
     */
    function renderPagination(tabKey, currentPage, totalPages, totalItems, searchParams) {
      var $paginationContainer = $('#' + tabKey + 'Pagination')
      if (totalPages <= 1) {
        $paginationContainer.html('')
        return
      }
      laypage.render({
        elem: $paginationContainer[0],
        count: totalItems,
        limit: 10,
        curr: currentPage,
        layout: ['count', 'prev', 'page', 'next', 'skip'],
        jump: function (obj, first) {
          if (!first) {
            loadAppointments(tabKey, obj.curr, searchParams)
          }
        },
      })
    }

    // Tab切换事件
    element.on('tab(appointmentTabs)', function (data) {
      var tab = $(this).data('key')
      if (tab) {
        currentTab = tab
        if (currentTab !== 'calendar') {
          loadAppointments(currentTab, 1, currentSearch)
        } else {
          // 延迟初始化日历，确保DOM元素已经显示
          setTimeout(function () {
            initCalendar()
          }, 50)
        }
      }
    })

    // 搜索按钮点击事件
    $('#searchBtn').on('click', function () {
      currentSearch = {
        q: $('#appointmentSearch').val(),
        status: $('#statusFilter').val(),
        date_range: $('#dateRangeFilter').val(),
      }
      loadAppointments(currentTab, 1, currentSearch)
    })

    // 重置搜索并加载
    function resetAndLoad() {
      $('#appointmentSearch').val('')
      $('#statusFilter').val('')
      $('#dateRangeFilter').val('')
      form.render('select')
      currentSearch = { q: '', status: '', date_range: '' }
      loadAppointments(currentTab, 1, currentSearch)
    }

    // 初始化页面，加载第一个tab
    loadAppointments(currentTab, 1, currentSearch)

    // --- 日历视图逻辑 ---
    var calendar = null
    function initCalendar() {
      var calendarEl = document.getElementById('appointmentCalendar')
      if (!calendarEl) {
        layer.msg('无法找到日历容器', { icon: 2 })
        return
      }

      try {
        if (!calendar) {
          // 检查FullCalendar是否已加载
          if (typeof FullCalendar === 'undefined') {
            layer.msg('日历组件未加载', { icon: 2 })
            return
          }

          // 确保日历容器可见
          $(calendarEl).html('<div style="height: 500px; width: 100%;"></div>')

          calendar = new FullCalendar.Calendar(calendarEl, {
            initialView: 'dayGridMonth',
            locale: 'zh-cn',
            headerToolbar: {
              left: 'prev,next today',
              center: 'title',
              right: 'dayGridMonth,timeGridWeek,listWeek',
            },
            events: function (fetchInfo, successCallback, failureCallback) {
              // 显示加载中提示
              layer.load(1, { shade: [0.1, '#fff'] })

              $.ajax({
                url: '/api/appointments/doctor-all',
                type: 'GET',
                success: function (res) {
                  layer.closeAll('loading')
                  if (res.status === 'success') {
                    var events = res.data.map(function (appt) {
                      // 根据预约状态设置不同颜色
                      var color
                      switch (appt.status && appt.status.value) {
                        case 'pending':
                          color = '#FF9900'
                          break // 橙色
                        case 'confirmed':
                          color = '#3CB371'
                          break // 绿色
                        case 'completed':
                          color = '#A9A9A9'
                          break // 灰色
                        case 'cancelled':
                          color = '#DC143C'
                          break // 红色
                        case 'rejected':
                          color = '#B22222'
                          break // 深红色
                        default:
                          color = '#1E90FF' // 默认蓝色
                      }

                      return {
                        id: appt.appointment_id,
                        title: appt.patient_name,
                        start: appt.appointment_date,
                        color: color,
                        extendedProps: appt,
                      }
                    })
                    successCallback(events)
                  } else {
                    layer.msg(res.message || '加载失败', { icon: 2 })
                    failureCallback(new Error('Failed to load events'))
                  }
                },
                error: function () {
                  layer.closeAll('loading')
                  layer.msg('网络错误，加载日历数据失败', { icon: 2 })
                  failureCallback(new Error('Network error'))
                },
              })
            },
            eventClick: function (info) {
              viewAppointmentDetail(info.event.id)
            },
            // 减少重绘延迟
            rerenderDelay: 10,
            // 日期格式本地化
            eventTimeFormat: {
              hour: '2-digit',
              minute: '2-digit',
              hour12: false,
            },
          })

          // 确保日历正确渲染
          calendar.render()

          // 窗口大小变化时重新渲染日历
          $(window).on('resize', function () {
            if (calendar) calendar.updateSize()
          })
        } else {
          // 如果日历已经初始化，只需刷新事件
          calendar.refetchEvents()
        }
      } catch (err) {
        layer.msg('初始化日历失败: ' + err.message, { icon: 2 })
      }
    }

    // 将重要函数暴露到全局作用域
    window.reloadCurrentTabData = function () {
      // 重新加载当前活动的tab页数据
      var activeTabKey = $('.layui-tab-title .layui-this').data('key')
      if (activeTabKey === 'calendar') {
        if (calendar) calendar.refetchEvents()
      } else {
        loadAppointments(activeTabKey, 1, currentSearch)
      }
    }

    // 模块化重构：创建预约
    setupAppointmentCreation(form, laydate, layer, $)
  })
}

// --- 操作函数 (暴露到全局) ---
function confirmAppointment(id) {
  if (!window.layui_layer) {
    console.error('Layui layer 组件未加载')
    return
  }

  window.layui_layer.confirm(
    '您确定要确认此预约吗？',
    { icon: 3, title: '提示' },
    function (index) {
      $.ajax({
        url: '/api/appointments/' + id + '/confirm',
        type: 'POST',
        contentType: 'application/json', // 指定内容类型为JSON
        data: JSON.stringify({}), // 发送一个空的JSON对象
        success: function (res) {
          if (res.status === 'success') {
            window.layui_layer.msg('已确认', { icon: 1, time: 1500 })
            // 调用全局函数
            window.reloadCurrentTabData()
          } else {
            window.layui_layer.msg(res.message || '操作失败', { icon: 2, time: 2000 })
          }
        },
        error: function (xhr) {
          var errorMsg = '网络错误，操作失败'
          if (xhr.responseJSON && xhr.responseJSON.message) {
            errorMsg = xhr.responseJSON.message
          }
          window.layui_layer.msg(errorMsg, { icon: 2, time: 2000 })
        },
      })
      window.layui_layer.close(index)
    }
  )
}

function rejectAppointment(id) {
  layer.prompt(
    {
      formType: 2,
      value: '',
      title: '请输入拒绝理由（必填）',
      area: ['300px', '150px'], //自定义文本域宽高
    },
    function (value, index, elem) {
      $.ajax({
        url: '/api/appointments/' + id + '/reject',
        type: 'POST',
        contentType: 'application/json', // 指定内容类型为JSON
        data: JSON.stringify({ reason: value }), // 将数据转换为JSON字符串
        success: function (res) {
          if (res.status === 'success') {
            layer.msg('已拒绝', { icon: 1, time: 1500 })
            reloadCurrentTabData()
          } else {
            layer.msg(res.message || '操作失败', { icon: 2, time: 2000 })
          }
        },
        error: function (xhr) {
          var errorMsg = '网络错误，操作失败'
          if (xhr.responseJSON && xhr.responseJSON.message) {
            errorMsg = xhr.responseJSON.message
          }
          layer.msg(errorMsg, { icon: 2, time: 2000 })
        },
      })
      layer.close(index)
    }
  )
}

function completeAppointment(id) {
  // 暂时只要求确认，不要求填写诊断信息，后续可以扩展
  layer.confirm('确定该患者的诊疗已完成？', { icon: 3, title: '提示' }, function (index) {
    $.ajax({
      url: '/api/appointments/' + id + '/complete',
      type: 'POST',
      contentType: 'application/json', // 指定内容类型为JSON
      data: JSON.stringify({}), // 发送一个空的JSON对象
      success: function (res) {
        if (res.status === 'success') {
          layer.msg('操作成功', { icon: 1, time: 1500 })
          reloadCurrentTabData()
        } else {
          layer.msg(res.message || '操作失败', { icon: 2, time: 2000 })
        }
      },
      error: function (xhr) {
        var errorMsg = '网络错误，操作失败'
        if (xhr.responseJSON && xhr.responseJSON.message) {
          errorMsg = xhr.responseJSON.message
        }
        layer.msg(errorMsg, { icon: 2, time: 2000 })
      },
    })
    layer.close(index)
  })
}

function viewAppointmentDetail(id) {
  $.get('/api/appointments/' + id + '/details', function (res) {
    if (res.status === 'success' && res.data) {
      var data = res.data
      var content = `
                <div style="padding: 20px;">
                    <p><strong>患者:</strong> ${data.patient_name || '无'}</p>
                    <p><strong>预约类型:</strong> ${data.type_name || '无'}</p>
                    <p><strong>科室:</strong> ${data.department_name || '无'}</p>
                    <p><strong>预约时间:</strong> ${data.appointment_date || ''} ${
        (data.time_slot && data.time_slot.display_name) || ''
      }</p>
                    <p><strong>状态:</strong> ${
                      (data.status && data.status.display_name) || '无'
                    }</p>
                    <p><strong>主诉:</strong> ${data.symptoms || '无'}</p>
                    <p><strong>申请时间:</strong> ${data.created_at || '无'}</p>
                        </div>
            `
      layer.open({
        type: 1,
        title: '预约详情',
        area: ['450px', 'auto'],
        content: content,
      })
    } else {
      layer.msg(res.message || '获取详情失败', { icon: 2 })
    }
  }).fail(function () {
    layer.msg('网络错误', { icon: 2 })
  })
}

// 模块化重构：创建预约
function setupAppointmentCreation(form, laydate, layer, $) {
  // 1. 定义弹窗内容的HTML模板
  const getAppointmentFormHtml = () => `
        <div style="padding: 20px;">
            <form id="createAppointmentForm" class="layui-form" lay-filter="createAppointmentForm">
                <!-- Patient Search -->
                <div class="layui-form-item">
                    <label class="layui-form-label">患者</label>
                    <div class="layui-input-block" style="position: relative;">
                        <input type="hidden" name="patient_id" id="patientIdInput" required lay-verify="required" title="请选择一位患者" />
                        <input type="text" name="patient_name" id="patientSearchInput" placeholder="搜索患者姓名、ID或联系方式"
                               autocomplete="off" class="layui-input" required lay-verify="required" />
                        <div id="patientSearchResults" style="display:none; position:absolute; z-index:19999999;
                               width:100%; max-height:250px; overflow-y:auto; background:#fff; border:1px solid #e6e6e6;
                               box-shadow: 0 4px 12px rgba(0,0,0,0.15); border-radius: 4px; top: 40px; left: 0;">
                        </div>
                    </div>
                </div>
                <!-- Other form items -->
                <div class="layui-form-item">
                    <label class="layui-form-label">预约类型</label>
                    <div class="layui-input-block">
                        <select name="appointment_type" lay-verify="required"><option value=""></option><option value="regular">常规门诊</option><option value="followup">复诊</option><option value="emergency">急诊</option><option value="consultation">会诊</option></select>
                    </div>
                </div>
                <div class="layui-form-item">
                    <label class="layui-form-label">科室</label>
                    <div class="layui-input-block">
                        <select name="department" lay-verify="required"><option value=""></option><option value="neurology">神经科</option><option value="cardiology">心脏科</option><option value="orthopedics">骨科</option><option value="internal">内科</option><option value="surgery">外科</option><option value="pediatrics">儿科</option><option value="gynecology">妇科</option><option value="ophthalmology">眼科</option><option value="other">其他</option></select>
                    </div>
                </div>
                <div class="layui-form-item">
                    <label class="layui-form-label">预约日期</label>
                    <div class="layui-input-block">
                        <div id="appointmentDateContainer" style="margin-bottom: 10px;"></div>
                        <input type="hidden" name="appointment_date" id="appointmentDateHiddenInput" lay-verify="required" />
                    </div>
                </div>
                <div class="layui-form-item">
                    <label class="layui-form-label">时间段</label>
                    <div class="layui-input-block">
                        <select name="time_slot" lay-verify="required"><option value="">请选择时间段</option><option value="morning">上午 (08:00-12:00)</option><option value="afternoon">下午 (13:00-17:00)</option></select>
                    </div>
                </div>
                <div class="layui-form-item layui-form-text">
                    <label class="layui-form-label">患者症状</label>
                    <div class="layui-input-block">
                        <textarea name="symptoms" placeholder="（选填）请输入患者主诉或症状描述" class="layui-textarea"></textarea>
                    </div>
                </div>
                <!-- Actions -->
                <div class="layui-form-item" style="margin-top: 30px;">
                    <div class="layui-input-block">
                        <button type="submit" class="layui-btn" lay-submit lay-filter="createAppointmentSubmit">立即提交</button>
                        <button type="reset" class="layui-btn layui-btn-primary">重置</button>
                    </div>
                </div>
            </form>
        </div>
    `

  // 2. 渲染患者搜索结果列表的函数
  function renderPatientList(patients, container) {
    if (!patients || patients.length === 0) {
      container
        .html(
          '<div class="search-result-empty"><i class="fas fa-user-slash"></i> 未找到匹配的患者</div>'
        )
        .show()
      return
    }
    let html = `<div class="search-result-header">找到 ${patients.length} 位患者</div>`
    patients.forEach(p => {
      const name = p.name || '未知姓名'
      const gender = p.gender || ''
      const age = p.age ? `${p.age}岁` : ''
      const contact = p.contact || '无联系方式'
      let genderIcon = ''
      if (gender === '男') genderIcon = '<i class="fas fa-male gender-male"></i>'
      else if (gender === '女') genderIcon = '<i class="fas fa-female gender-female"></i>'
      html += `
                <div class="patient-item" data-id="${p.id}" data-name="${name}">
                    <div class="patient-name">${name} ${genderIcon} <span class="patient-age">${age}</span></div>
                    <div class="patient-contact">ID: ${p.id} · ${contact}</div>
                </div>`
    })
    container.html(html).show()
  }

  let activeLayerIndex = null // 用于存储当前打开的弹窗实例索引

  // 3. "创建新预约"按钮点击事件：只负责打开弹窗和初始化内部组件
  $('#createAppointmentBtn').on('click', function () {
    activeLayerIndex = layer.open({
      type: 1,
      title: '创建新预约',
      area: ['580px', 'auto'],
      content: getAppointmentFormHtml(),
      success: function (layero, index) {
        // 渲染弹窗内部的组件
        form.render(null, 'createAppointmentForm')
        laydate.render({
          elem: '#appointmentDateContainer',
          position: 'static',
          min: 0,
          max: 14,
          showBottom: false,
          done: value => layero.find('#appointmentDateHiddenInput').val(value),
        })

        // 初始化弹窗内的搜索交互
        const searchInput = layero.find('#patientSearchInput')
        const searchResults = layero.find('#patientSearchResults')
        const patientIdField = layero.find('#patientIdInput')
        let searchTimer
        searchInput.on('keyup', function () {
          clearTimeout(searchTimer)
          const query = $(this).val().trim()
          if (query.length === 0) {
            searchResults.empty().hide()
            return
          }
          searchTimer = setTimeout(() => {
            searchResults
              .html(
                '<div class="search-result-loading"><i class="layui-icon layui-icon-loading layui-anim layui-anim-rotate"></i> 正在搜索...</div>'
              )
              .show()
            $.ajax({
              url: '/api/patient/search',
              type: 'GET',
              data: { q: query },
              dataType: 'json',
              success: data => renderPatientList(data, searchResults),
              error: () =>
                searchResults
                  .html(
                    '<div class="search-result-error"><i class="fas fa-exclamation-triangle"></i> 搜索服务出错</div>'
                  )
                  .show(),
            })
          }, 300)
        })

        searchResults.on('click', '.patient-item', function () {
          patientIdField.val($(this).data('id'))
          searchInput.val($(this).data('name'))
          searchResults.empty().hide()
        })
      },
      end: function () {
        // 弹窗销毁时，清空索引
        activeLayerIndex = null
      },
    })
  })

  // 4. 表单提交监听器：独立于弹窗创建，只定义一次
  form.on('submit(createAppointmentSubmit)', function (data) {
    if (!activeLayerIndex) return false // 如果没有活动的弹窗，则不执行

    const loading = layer.load(1)
    $.ajax({
      url: '/doctor/appointments/create',
      type: 'POST',
      data: data.field,
      success: function (res) {
        layer.close(loading)
        if (res.status === 'success') {
          // 使用存储的索引关闭正确的弹窗
          layer.close(activeLayerIndex)
          layer.msg('预约创建成功!', { icon: 1, time: 1500 })
          reloadCurrentTabData()
        } else {
          layer.msg(res.message || '操作失败，请重试', { icon: 2 })
        }
      },
      error: () => {
        layer.close(loading)
        layer.msg('服务器连接失败', { icon: 2 })
      },
    })
    return false // 阻止表单默认提交
  })
}
