document.addEventListener('DOMContentLoaded', function () {
  // 页面加载完成后，立即更新一次角标
  updateStatusTabCounts()

  // 立即检查一次表格内容以显示或隐藏"无结果"消息
  checkTableContent()
})

window.showNoResultsMessage = function (message) {
  var table = $('table.layui-table')
  if (!table.length) return

  var cardBody = table.closest('.layui-card-body')
  if (!cardBody.length) return

  // 移除旧的提示信息，以防重复
  $('#no-results-message').remove()

  // 隐藏表格和分页
  table.hide()
  $('#patient-pagination').hide()

  // 创建并添加新的提示信息容器
  var noResultsDiv = $('<div id="no-results-message"></div>').css({
    display: 'flex',
    'flex-direction': 'column',
    'justify-content': 'center',
    'align-items': 'center',
    'min-height': '250px',
    padding: '20px',
  })

  var icon = $(
    '<div class="no-results-icon"><i class="layui-icon layui-icon-face-smile"></i></div>'
  ).css({
    'font-size': '48px',
    'margin-bottom': '15px',
    color: '#1E9FFF',
  })

  var text = $('<p></p>').text(message).css({
    'font-size': '16px',
    'font-weight': '500',
    'margin-bottom': '10px',
    color: '#555',
  })

  var helpText = $('<p></p>')
    .html('您可以尝试：<br>1. 切换到其他状态标签<br>2. 重置筛选条件<br>3. 点击上方的"添加患者"按钮')
    .css({
      'font-size': '14px',
      color: '#888',
      'margin-top': '10px',
      'line-height': '1.5',
    })

  noResultsDiv.append(icon).append(text).append(helpText)

  cardBody.append(noResultsDiv)
}

window.hideNoResultsMessage = function () {
  var cardBody = $('#no-results-message').closest('.layui-card-body')

  $('#no-results-message').remove()

  if (cardBody.length) {
    // 恢复表格和分页的显示
    cardBody.find('table.layui-table').show()
    cardBody.find('#patient-pagination').show()
  }
}

function checkTableContent() {
  var tableBody = $('table.layui-table tbody')
  // 仅当表格存在时才继续
  if (tableBody.length === 0) return

  var visibleRows = tableBody.find('tr:visible').length
  var totalRows = tableBody.find('tr').length

  // 如果总行数为0（初始加载时可能没有数据），并且没有"无数据"的静态提示
  if (totalRows === 0 && $('.layui-empty').length === 0) {
    showNoResultsMessage('当前没有任何患者记录')
  } else if (totalRows > 0 && visibleRows === 0) {
    // 如果有数据但全部被隐藏（例如，通过状态过滤）
    var currentTab = $('.patient-filter-tabs .layui-tab-title li.layui-this').text().trim()
    var statusText = currentTab.replace(/\d+/g, '').trim()
    window.showNoResultsMessage('没有' + statusText + '状态的患者记录')
  } else {
    window.hideNoResultsMessage()
  }
}

function setupTableObserver() {
  var tableBody = document.querySelector('table.layui-table tbody')
  if (!tableBody) {
    setTimeout(setupTableObserver, 500)
    return
  }

  var observer = new MutationObserver(function (mutations) {
    checkTableContent()
  })

  var config = {
    childList: true,
    subtree: true,
    characterData: true,
  }

  observer.observe(tableBody, config)

  // 初始加载时检查
  // checkTableContent();

  $('.patient-filter-tabs .layui-tab-title li').on('click', function () {
    setTimeout(checkTableContent, 100)
  })
}

// 使用事件委托为备注按钮绑定点击事件
$(document).on('click', '.show-note-btn', function () {
  var patientId = $(this).data('id')
  var currentNote = $(this).data('note')
  showAddNoteDialog(patientId, currentNote, this)
})

layui.use('element', function () {
  var element = layui.element
  var $ = layui.jquery

  $('.patient-filter-tabs .layui-tab-title').on('click', 'li', function (e) {
    e.stopImmediatePropagation()

    var status = $(this).data('status')

    $(this).addClass('layui-this').siblings().removeClass('layui-this')

    if (typeof filterPatientsByStatus === 'function') {
      filterPatientsByStatus(status)
    } else {
      console.error('主过滤函数 filterPatientsByStatus 未找到。')
    }
  })
})

setupTableObserver()

function filterPatientsByStatus(status) {
  var tableRows = $('table.layui-table tbody tr')
  var visibleRows = 0

  tableRows.each(function () {
    var row = $(this)

    var rowStatus = row.find('td:nth-child(4) .layui-badge').text().trim()

    if (status === 'all' || rowStatus === status) {
      row.show()
      visibleRows++
    } else {
      row.hide()
    }
  })

  if (visibleRows > 0) {
    hideNoResultsMessage()
  } else {
    showNoResultsMessage('没有' + status + '状态的患者记录')
  }

  var visibleItems = $('table.layui-table tbody tr:visible')
  if (typeof updatePagination === 'function') {
    updatePagination(visibleItems.length, 1, visibleItems)
  }
}

// =========================================================================
// 新增：备注弹窗功能 和 状态角标更新
// =========================================================================

/**
 * 更新顶部状态标签的患者数量角标
 */
function updateStatusTabCounts() {
  $.ajax({
    url: '/api/patient/status_counts',
    type: 'GET',
    success: function (res) {
      if (res.success) {
        const counts = res.counts
        updateCountBadge('#pendingCount', counts['待就诊'] || 0)
        updateCountBadge('#treatmentCount', counts['治疗中'] || 0)
        updateCountBadge('#followupCount', counts['随访中'] || 0)
        updateCountBadge('#completedCount', counts['已完成'] || 0)
      }
    },
  })
}

function updateCountBadge(selector, count) {
  const badge = $(selector)
  if (badge.length) {
    if (count > 0) {
      badge.text(count).show()
    } else {
      badge.hide()
    }
  }
}

/**
 * 显示添加/编辑备注的弹窗
 * @param {string} patientId - 患者ID
 * @param {string} currentNote - 当前的备注内容
 * @param {HTMLElement} buttonElement - 被点击的按钮元素
 */
function showAddNoteDialog(patientId, currentNote, buttonElement) {
  layer.prompt({
    formType: 2,
    value: currentNote,
    title: '编辑患者备注',
    area: ['400px', '250px'],
    btn: ['确定', '取消'],
    yes: function (index, layero) {
      var note = layero.find('.layui-layer-input').val()

      $.ajax({
        url: '/doctor/patient/' + patientId + '/add-note',
        type: 'POST',
        data: {
          note: note,
        },
        success: function (res) {
          if (res.status === 'success') {
            layer.msg('备注更新成功', { icon: 1 })

            // 更新按钮状态和data-note属性
            var $button = $(buttonElement)
            $button.data('note', note)

            if (note.trim() !== '') {
              $button.removeClass('btn-fresh-text').addClass('btn-fresh-warning')
              $button
                .find('.layui-icon')
                .removeClass('layui-icon-add-1')
                .addClass('layui-icon-edit')
              $button.find('i').next().remove()
              $button.append(' 查看备注')
            } else {
              $button.removeClass('btn-fresh-warning').addClass('btn-fresh-text')
              $button
                .find('.layui-icon')
                .removeClass('layui-icon-edit')
                .addClass('layui-icon-add-1')
              $button.find('i').next().remove()
              $button.append(' 备注')
            }

            layer.close(index)
          } else {
            layer.alert('更新失败: ' + res.message, { icon: 2 })
          }
        },
        error: function () {
          layer.alert('请求失败，请检查网络连接。', { icon: 2 })
        },
      })
    },
  })
}
