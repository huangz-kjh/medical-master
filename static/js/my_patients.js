// 防止患者添加成功后出现请选择患者弹窗的逻辑错误
window.isPatientAddSuccess = false
// 设置全局锁，防止所有弹窗
window.isSubmitting = false
// 当前选中的患者状态过滤
window.currentStatusFilter = 'all'
// 分页设置
window.patientPagination = {
  currentPage: 1,
  pageSize: 10,
  totalPatients: 0,
  totalPages: 1,
}

// 检查URL参数，判断是否是添加后刷新
$(document).ready(function () {
  // 获取URL中的参数
  var urlParams = new URLSearchParams(window.location.search)
  if (urlParams.has('action') && urlParams.get('action') === 'patient_added') {
    // 设置标记，防止验证
    window.isPatientAddSuccess = true

    // 修改页面标题暂时显示添加成功
    var originalTitle = document.title
    document.title = '添加成功 - ' + originalTitle
    setTimeout(function () {
      document.title = originalTitle
    }, 2000)

    // 清除URL参数，避免刷新页面时重复检测
    if (history.pushState) {
      var newurl = window.location.protocol + '//' + window.location.host + window.location.pathname
      window.history.pushState({ path: newurl }, '', newurl)
    }
  }
})

// 安全页面刷新方法 - 改进版
function safeReloadPage(action) {
  // 设置锁，阻止所有弹窗显示
  window.isSubmitting = true
  window.isPatientAddSuccess = true

  // 移除所有可能的检验和验证事件
  $(document).off('click.patient_validation')

  // 关闭所有可能的弹窗
  if (typeof layer !== 'undefined') {
    layer.closeAll()
  }

  // 带参数刷新页面
  var url = window.location.pathname
  if (action) {
    url += '?action=' + action + '&t=' + new Date().getTime()
  }

  // 延迟跳转确保所有弹窗关闭
  setTimeout(function () {
    window.location.href = url
  }, 500)
}

// 自定义弹窗管理
var CustomModal = {
  // 当前打开的弹窗的ID
  currentModalId: null,

  // 打开弹窗
  open: function (modalId) {
    // 关闭可能存在的其他弹窗
    if (this.currentModalId && this.currentModalId !== modalId) {
      this.close(this.currentModalId)
    }

    // 打开新弹窗
    var $modal = $('#' + modalId)
    $modal.fadeIn(200)

    // 禁止背景滚动
    $('body').css('overflow', 'hidden')

    // 记录当前弹窗ID
    this.currentModalId = modalId

    // 设置拖拽（使用jQuery UI如果已加载）
    if ($.fn.draggable) {
      $modal.find('.custom-modal-content').draggable({
        handle: '.custom-modal-header',
        containment: 'window',
      })
    }

    // 触发打开事件
    $(document).trigger('customModal:opened', [modalId])

    return $modal
  },

  // 关闭弹窗
  close: function (modalId) {
    var $modal = typeof modalId === 'string' ? $('#' + modalId) : modalId
    $modal.fadeOut(200)

    // 恢复背景滚动
    $('body').css('overflow', '')

    // 清除当前弹窗ID（如果是当前弹窗）
    if (this.currentModalId === (typeof modalId === 'string' ? modalId : $modal.attr('id'))) {
      this.currentModalId = null
    }

    // 触发关闭事件
    $(document).trigger('customModal:closed', [
      typeof modalId === 'string' ? modalId : $modal.attr('id'),
    ])
  },
}

// 全局变量初始化
window.isPatientAddSuccess = false

// 全局错误提示函数
function showErrorMessage(message, focusElement) {
  // 如果设置了成功添加标记或正在提交中，不显示错误提示
  if (window.isPatientAddSuccess || window.isSubmitting) {
    console.log(
      '跳过错误提示:',
      message,
      '提交状态:',
      window.isSubmitting,
      '成功状态:',
      window.isPatientAddSuccess
    )
    return
  }

  layui.use('layer', function () {
    var layer = layui.layer

    // 再次检查锁定状态（避免延迟加载期间状态变化）
    if (window.isSubmitting || window.isPatientAddSuccess) {
      console.log('layui加载后再次检查 - 跳过错误提示')
      return
    }

    layer.open({
      type: 1,
      title: '提示',
      content: '<div class="error-message"><span class="error-text">' + message + '</span></div>',
      area: ['350px', 'auto'],
      skin: 'error-message-dialog',
      btn: ['确定'],
      btnAlign: 'c',
      yes: function (index) {
        layer.close(index)
        if (focusElement && typeof focusElement === 'object') {
          focusElement.focus()
        } else if (typeof focusElement === 'string') {
          $(focusElement).focus()
        }
      },
    })
  })
}

// 更新所有搜索错误提示的样式 - 应用相同的风格，移除感叹号图标 - 改进版
function showSearchError(element, message) {
  // 检查锁定状态
  if (window.isSubmitting || window.isPatientAddSuccess) {
    console.log('跳过搜索错误提示:', message)
    return
  }

  $(element)
    .html('<li style="padding:10px;color:#f00;text-align:center;">' + message + '</li>')
    .show()
}

layui.use(['form', 'layer', 'element', 'laydate'], function () {
  var form = layui.form
  var layer = layui.layer
  var element = layui.element
  var laydate = layui.laydate
  var $ = layui.jquery

  // 存储全局医生ID
  var doctorId = $('#doctorIdData').data('id') || parseInt("{{ session.get('user_id', 0) }}")

  // 日期选择器
  laydate.render({
    elem: '#appointment_date',
    min: 0, // 最小可选择为当前日期
  })

  // 设置自定义弹窗关闭按钮事件
  $(document).on('click', '.custom-modal-close, .custom-modal-cancel', function () {
    var modalId = $(this).closest('.custom-modal').attr('id')
    CustomModal.close(modalId)
  })

  // 点击遮罩不关闭
  $(document).on('click', '.custom-modal-mask', function (e) {
    e.stopPropagation()
  })

  // =========================================================================
  // 新版：添加患者弹窗逻辑 (重构)
  // =========================================================================
  function setupPatientAddition() {
    const addBtn = $('#addPatientBtn')
    let searchTimeout
    let popupIndex // 用于存储弹窗实例的索引

    // 1. 点击 "添加患者" 按钮
    addBtn.on('click', function () {
      // 动态创建弹窗内容
      const popupContent = `
        <div style="padding: 25px;">
          <form class="layui-form" id="addPatientForm" lay-filter="addPatientForm">
            <!-- 搜索患者 -->
            <div class="layui-form-item">
              <label class="layui-form-label">搜索患者</label>
              <div class="layui-input-block">
                <input
                  type="text"
                  id="patient-search-input"
                  name="patientSearch"
                  placeholder="输入姓名、手机号或身份证号搜索"
                  autocomplete="off"
                  class="layui-input"
                />
                <div
                  id="patient-search-results"
                  class="layui-card"
                  style="
                    display: none;
                    position: absolute;
                    z-index: 9999;
                    width: 100%;
                    max-height: 200px;
                    overflow-y: auto;
                    background-color: #fff;
                    border: 1px solid #ddd;
                  "
                >
                  <div class="layui-card-body" style="padding: 0">
                    <ul class="layui-menu"></ul>
                  </div>
                </div>
              </div>
            </div>
            <input type="hidden" name="selected_patient_id" id="selected_patient_id" />

            <!-- 关系类型 -->
            <div class="layui-form-item">
              <label class="layui-form-label">关系类型</label>
              <div class="layui-input-block">
                <select name="relationship_type" lay-verify="required">
                  <option value=""></option>
                  <option value="家庭成员">家庭成员</option>
                  <option value="朋友">朋友</option>
                  <option value="同事">同事</option>
                  <option value="监护人">监护人</option>
                  <option value="其他">其他</option>
                </select>
              </div>
            </div>

            <!-- 备注 -->
            <div class="layui-form-item layui-form-text">
              <label class="layui-form-label">备注</label>
              <div class="layui-input-block">
                <textarea
                  name="remarks"
                  placeholder="请输入备注信息 (可选)"
                  class="layui-textarea"
                ></textarea>
              </div>
            </div>

            <!-- 操作按钮 -->
            <div class="layui-form-item" style="text-align: right; margin-top: 20px">
              <button type="button" class="layui-btn layui-btn-primary" id="cancel-add-patient">
                取消
              </button>
              <button class="layui-btn" lay-submit lay-filter="confirmAddPatient">确认添加</button>
            </div>
          </form>
        </div>
      `

      popupIndex = layer.open({
        type: 1,
        title: '添加新患者关联',
        area: ['550px', 'auto'], // 设置合理的宽度
        shadeClose: false,
        content: popupContent, // 使用动态创建的内容
        success: function (layero, index) {
          // 弹窗成功后重置表单并渲染
          form.render() // 重新渲染layui表单元素

          // 绑定搜索框输入事件
          $(layero)
            .find('#patient-search-input')
            .on(
              'input',
              debounce(function () {
                const query = $(this).val().trim()
                const resultsContainer = $(layero).find('#patient-search-results')
                const resultsList = resultsContainer.find('.layui-menu')

                if (query.length < 1) {
                  resultsContainer.hide()
                  return
                }

                $.ajax({
                  url: '/api/patients/search',
                  type: 'GET',
                  data: { q: query },
                  success: function (res) {
                    resultsList.empty()
                    if (res.status === 'success' && res.data.length > 0) {
                      res.data.forEach(function (patient) {
                        const itemHtml = `<li class="layui-menu-item" data-id="${patient.patient_id}" data-name="${patient.name}">${patient.name} - ${patient.contact_info}</li>`
                        resultsList.append(itemHtml)
                      })
                      resultsContainer.show()
                    } else {
                      resultsList.append('<li class="layui-menu-item-disabled">无匹配结果</li>')
                      resultsContainer.show()
                    }
                  },
                  error: function () {
                    resultsList.empty()
                    resultsList.append(
                      '<li class="layui-menu-item-disabled" style="color: red;">搜索失败</li>'
                    )
                    resultsContainer.show()
                  },
                })
              }, 300)
            )

          // 绑定搜索结果点击事件
          $(layero).on('click', '.layui-menu-item', function () {
            if ($(this).hasClass('layui-menu-item-disabled')) return

            const patientId = $(this).data('id')
            const patientName = $(this).data('name')

            $(layero).find('#patient-search-input').val(patientName)
            $(layero).find('#selected_patient_id').val(patientId)
            $(layero).find('#patient-search-results').hide()
          })

          // 绑定点击页面其他地方隐藏搜索结果
          $(document).on('click', function (e) {
            if (!$(e.target).closest('#patient-search-input, #patient-search-results').length) {
              $(layero).find('#patient-search-results').hide()
            }
          })

          // 绑定取消按钮
          $(layero)
            .find('#cancel-add-patient')
            .on('click', function () {
              layer.close(index)
            })
        },
        cancel: function () {
          // 点击右上角关闭按钮的回调
          return true // 允许关闭
        },
      })

      // 使用 layui 的方式处理表单提交
      form.on('submit(confirmAddPatient)', function (data) {
        const formData = data.field // 获取表单数据
        const patientId = $('#selected_patient_id').val()

        if (!patientId) {
          layer.msg('请先搜索并选择一个患者。', { icon: 5 })
          return false // 阻止表单提交
        }

        // 准备要发送到后端的数据
        const submissionData = {
          patient_id: patientId,
          relationship_type: formData.relationship_type,
          remarks: formData.remarks,
        }

        $.ajax({
          url: '/doctor/patient/add-relation',
          type: 'POST',
          data: submissionData,
          success: function (res) {
            if (res.status === 'success') {
              layer.msg(res.message, { icon: 1, time: 1500 }, function () {
                layer.close(popupIndex) // 关闭当前弹窗
                window.location.reload() // 刷新页面
              })
            } else {
              layer.alert(res.message || '添加失败，请重试。', { icon: 2 })
            }
          },
          error: function () {
            layer.alert('网络请求失败，请检查网络后重试。', { icon: 2 })
          },
        })

        return false // 必须返回false，阻止表单默认提交
      })
    })
  }

  // 绑定基础事件
  function bindBasicEvents() {
    // 初始化日期选择器
    laydate.render({
      elem: '#dob',
      trigger: 'click',
    })

    // 初始化状态tab切换事件
    element.on('tab(patientStatus)', function (data) {
      var status = $(this).attr('lay-id')
      filterPatientsByStatus(status)
    })

    // 搜索功能
    $('#searchInput').on(
      'input',
      debounce(function () {
        filterPatientsByStatus(window.currentStatusFilter)
      }, 300)
    )

    // 绑定患者相关操作按钮
    bindPatientActionButtons()

    // 初始化"添加患者"弹窗逻辑
    setupPatientAddition()
  }

  // 绑定患者操作按钮
  function bindPatientActionButtons() {
    // 查看医疗档案按钮
    $(document).on('click', '.view-record-btn', function () {
      var patientId = $(this).data('id')
      window.location.href = '/patients/' + patientId + '/detail'
    })

    // 展示患者预约记录
    $(document).on('click', '.view-appointments-btn', function () {
      var patientId = $(this).data('id')
      var patientName = $(this).data('name')
      showPatientAppointments(patientId, patientName)
    })

    // 修改患者状态
    $(document).on('click', '.change-status-btn', function () {
      var patientId = $(this).data('id')
      var patientName = $(this).data('name')
      var currentStatus = $(this).data('status')
      showChangePatientStatus(patientId, patientName, currentStatus)
    })

    // 点击"治疗"按钮
    $('.treat-btn').on('click', function (e) {
      e.preventDefault()
      var url = $(this).attr('href')
      var title = $(this).data('title') || '患者治疗记录'
      layer.open({
        type: 2,
        title: title,
        content: url,
        area: ['95%', '95%'],
        maxmin: true,
      })
    })
  }

  // 更新顶部状态计数
  function updatePatientStatusCounts() {
    var counts = {
      all: 0,
      active: 0,
      pending: 0,
      completed: 0,
      cancelled: 0,
    }

    $('tbody tr').each(function () {
      var status = $(this).data('status')
      counts.all++
      if (counts.hasOwnProperty(status)) {
        counts[status]++
      }
    })

    for (var status in counts) {
      $('#status-count-' + status).text(counts[status])
    }
  }

  // 显示无结果消息
  function showNoResultsMessage(message) {
    // 先移除所有旧的提示卡片，但保留原始的空状态提示
    $('#noResultsMessage').remove()

    // 创建新的提示HTML
    var noResultsHtml =
      '<div id="noResultsMessage" class="layui-empty" style="padding: 40px 0; text-align: center; background-color: #f9f9f9; border-radius: 4px; margin: 20px 0;">' +
      '<i class="layui-icon layui-icon-face-surprised" style="font-size: 56px; color: #FF9800; display: block; margin-bottom: 15px;"></i>' +
      '<p style="font-size: 16px; color: #555; margin-bottom: 10px;">' +
      message +
      '</p>' +
      '<p style="font-size: 14px; color: #888; margin-bottom: 15px;">可以尝试更改搜索条件</p>' +
      '</div>'

    // 确保只添加一次，先检查表格内容
    if ($('tbody tr:visible').length === 0) {
      // 查找表格元素并在之后添加提示
      $('table.layui-table').after(noResultsHtml)
    }
  }

  // 根据状态和搜索词过滤患者
  function filterPatientsByStatus(status) {
    var searchText = $('#searchInput').val().toLowerCase()
    window.currentStatusFilter = status

    $('tbody tr').each(function () {
      var row = $(this)
      var patientName = row.find('td:nth-child(2)').text().toLowerCase()
      var patientIdCard = row.find('td:nth-child(3)').text().toLowerCase()
      var rowStatus = row.data('status')

      var statusMatch = status === 'all' || rowStatus === status
      var searchMatch = patientName.includes(searchText) || patientIdCard.includes(searchText)

      if (statusMatch && searchMatch) {
        row.show()
        row.addClass('status-filtered')
      } else {
        row.hide()
        row.removeClass('status-filtered')
      }
    })
    updatePagination()
  }

  // 防抖函数
  function debounce(func, wait) {
    var timeout
    return function () {
      var context = this,
        args = arguments
      clearTimeout(timeout)
      timeout = setTimeout(function () {
        func.apply(context, args)
      }, wait)
    }
  }

  // 初始化页面
  bindBasicEvents()
  updatePatientStatusCounts()
  initPatientPagination()
})

// 初始化分页功能
function initPatientPagination() {
  // 计算总页数和总患者数
  var totalPatients = $('tbody tr').length
  window.patientPagination.totalPatients = totalPatients
  window.patientPagination.totalPages =
    Math.ceil(totalPatients / window.patientPagination.pageSize) || 1

  // 使用layui分页
  layui.use('laypage', function () {
    var laypage = layui.laypage

    // 渲染分页
    laypage.render({
      elem: 'patient-pagination',
      count: window.patientPagination.totalPatients,
      limit: window.patientPagination.pageSize,
      curr: window.patientPagination.currentPage,
      layout: ['count', 'prev', 'page', 'next', 'skip'],
      jump: function (obj, first) {
        // 首次不执行，避免初始化时重复渲染
        if (!first) {
          // 记录当前页码
          window.patientPagination.currentPage = obj.curr

          // 显示当前页数据
          showCurrentPage()
        }
      },
    })

    // 初始显示第一页数据
    showCurrentPage()
  })
}

// 更新分页控件
function updatePagination() {
  layui.use('laypage', function () {
    var laypage = layui.laypage

    // 计算过滤后的总数
    var filteredTotal =
      window.currentStatusFilter === 'all' ? $('tbody tr').length : $('.status-filtered').length

    window.patientPagination.totalPatients = filteredTotal
    window.patientPagination.totalPages =
      Math.ceil(filteredTotal / window.patientPagination.pageSize) || 1
    window.patientPagination.currentPage = 1 // 重置为第一页

    // 重新渲染分页
    laypage.render({
      elem: 'patient-pagination',
      count: filteredTotal,
      limit: window.patientPagination.pageSize,
      curr: 1,
      layout: ['count', 'prev', 'page', 'next', 'skip'],
      jump: function (obj, first) {
        if (!first) {
          window.patientPagination.currentPage = obj.curr
          showCurrentPage()
        }
      },
    })

    // 显示当前页数据
    showCurrentPage()

    // 显示无结果提示（如果需要）
    if (filteredTotal === 0) {
      showNoResultsMessage('没有找到匹配的患者记录')
    }
  })
}

// 显示当前页的患者记录
function showCurrentPage() {
  // 获取所有患者行
  var $rows = $('tbody tr')

  // 先隐藏所有行
  $rows.hide()

  // 计算当前页应显示的记录范围
  var startIndex = (window.patientPagination.currentPage - 1) * window.patientPagination.pageSize
  var endIndex = startIndex + window.patientPagination.pageSize

  // 显示符合条件的行
  if (window.currentStatusFilter === 'all') {
    // 如果是全部，则按原始顺序显示
    $rows.slice(startIndex, endIndex).show()
  } else {
    // 如果是按状态过滤，则仅显示匹配状态的行
    $('.status-filtered').slice(startIndex, endIndex).show()
  }
}
