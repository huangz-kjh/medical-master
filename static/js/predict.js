// 检查layui是否已加载
function initPredictModule() {
  if (typeof layui === 'undefined') {
    console.error('Layui 库未加载，1秒后重试')
    setTimeout(initPredictModule, 1000)
    return
  }

  layui.use(['layer', 'form', 'element'], function () {
    var layer = layui.layer
    var form = layui.form
    var element = layui.element

    // 从URL获取患者ID并存储，以确保每个页面的ID是独立的
    var patientIdFromUrl = new URLSearchParams(window.location.search).get('patient_id')
    if (patientIdFromUrl) {
      console.log('当前页面关联的患者ID:', patientIdFromUrl)
    }

    // 全局变量，用于存储当前影像分析记录的ID
    var currentImagingId = null

    // 当前选中的器官
    var selectedOrgan = null
    // 切片相关参数
    var maxSliceCount = 100 // 默认最大层数
    var currentSliceIndex = 50 // 默认当前层数
    var lastViewDim = 0 // 上次查看的维度
    // 添加示例图像标志
    var usedDemoImage = false
    // 添加页面状态标记，防止重复操作
    var isProcessing = false

    // 检查是否在iframe中嵌入
    var isEmbedded = window.isEmbedded || window.parent !== window
    // console.log('预测模块初始化 - iframe模式:', isEmbedded);

    // 添加CSS样式用于高亮器官选择区域
    $(
      '<style>.highlight-section { animation: pulse 1s infinite; } @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.6; } 100% { opacity: 1; }}</style>'
    ).appendTo('head')

    // 修改预测模块初始化部分，增加必要的事件监听和改进界面响应逻辑

    // ...这里是原始的代码...

    // 如果在iframe中嵌入，通知父窗口已加载
    if (isEmbedded) {
      // 通知父窗口预测模块已准备就绪
      setTimeout(function () {
        try {
          window.parent.postMessage('predict-module-ready', '*')
          // console.log('已通知父窗口predict-module-ready');
        } catch (e) {
          console.error('通知父窗口失败:', e)
        }
      }, 1000)
    }

    // 完全重置模块到初始状态
    function resetModule() {
      // 立即关闭所有弹窗和加载状态
      if (typeof layer !== 'undefined') {
        layer.closeAll()
      }
      $('.loading-overlay').hide()

      // 立即隐藏结果和切片区域
      $('#resultSection').hide().empty()
      $('#sliceSection').hide().empty()

      // 重置状态变量
      isProcessing = false
      selectedOrgan = null
      usedDemoImage = false
      maxSliceCount = 100
      currentSliceIndex = 50
      lastViewDim = 0

      // 重置文件输入和显示
      $('#fileInput').val('')
      $('#fileNameDisplay').text('')

      // 重置器官选择 - 确保没有任何一个器官被选中
      $('.organ-buttons button').removeClass('active')

      // 重置切片图像和相关控件
      $('#sliceImageContainer').html(
        '<div class="layui-text tip-text">选择视角和层数以查看切片</div>'
      )
      $('#savedSlicesGrid').empty()
      $('#savedSlicesContainer').hide()
      updateSliceControls()

      // 解绑所有动态添加的事件监听器
      $('#retryBtn, #demoImageBtn').off('click')

      // 立即滚动到页面顶部
      window.scrollTo(0, 0)
    }

    // 初始化界面
    function initInterface() {
      // 隐藏结果和切片区域
      $('#resultSection, #sliceSection').hide()

      // 器官按钮高亮重置 - 确保不选中任何器官
      $('.organ-buttons button').removeClass('active')
      selectedOrgan = null

      // 清空文件名显示
      $('#fileNameDisplay').text('')

      // 重置示例图像标志
      usedDemoImage = false

      // 清空已保存切片
      $('#savedSlicesGrid').empty()
      $('#savedSlicesContainer').hide()

      // 重置切片参数
      currentSliceIndex = 50
      maxSliceCount = 100
      updateSliceControls()

      // 重置切片图像
      $('#sliceImageContainer').html(
        '<div class="layui-text tip-text">选择视角和层数以查看切片</div>'
      )
    }

    // 更新切片控制器
    function updateSliceControls() {
      $('#currentSliceIndex').text(currentSliceIndex)
      $('#totalSliceCount').text(maxSliceCount)
      $('#sliceIndex').val(currentSliceIndex)
      $('#sliceSlider').val(currentSliceIndex).attr('max', maxSliceCount)
    }

    // 加载切片函数
    function loadSlice() {
      var dim = $('input[name="dim"]:checked').val()
      var index = currentSliceIndex
      lastViewDim = dim

      // 防止重复请求
      if (isProcessing) {
        // console.log('正在处理中，忽略重复请求');
        return
      }

      isProcessing = true
      // 显示加载动画
      layer.load(1, { shade: [0.1, '#fff'] })

      $.ajax({
        url: '/view_slice',
        type: 'GET',
        data: { dim: dim, index: index },
        success: function (response) {
          layer.closeAll('loading')
          isProcessing = false

          if (response.slice_img) {
            $('#sliceImageContainer').html(
              '<img src="data:image/png;base64,' +
                response.slice_img +
                '" alt="MRI切片" style="max-width:100%;">'
            )
          } else if (response.error) {
            layer.msg(response.error, { icon: 2 })
          }
        },
        error: function (xhr) {
          layer.closeAll('loading')
          isProcessing = false

          if (xhr.responseJSON && xhr.responseJSON.error) {
            layer.msg('加载切片失败：' + xhr.responseJSON.error, { icon: 2 })
          } else {
            layer.msg('加载切片失败，请重试', { icon: 2 })
          }
        },
      })
    }

    // 初始化页面时调用
    initInterface()

    // 统一处理错误并显示带有重试按钮的错误页面
    function handleError(errorMsg, statusCode) {
      // 立即隐藏加载动画
      $('.loading-overlay').hide()
      // 立即关闭所有弹窗
      if (typeof layer !== 'undefined') {
        layer.closeAll()
      }
      // 重置处理状态
      isProcessing = false
      // 清空内容区域
      $('#resultSection').hide().empty()
      $('#sliceSection').hide().empty()
      // 检查错误类型，提供适当的解决方案建议
      let errorTitle = '诊断失败'
      let solutionText = '请重试或联系技术支持。'
      if (errorMsg.includes('请上传 .nii 或 .nii.gz 格式的文件')) {
        errorTitle = '诊断失败：格式不支持'
        solutionText = '请确保上传的是 .nii 或 .nii.gz 格式的医学影像文件。'
      } else if (errorMsg.includes('无法读取文件') || errorMsg.includes('文件损坏')) {
        errorTitle = '诊断失败：文件读取错误'
        solutionText = '文件可能已损坏，请尝试上传另一个文件或使用示例图像。'
      } else if (errorMsg.includes('文件太大') || statusCode === 413) {
        errorTitle = '诊断失败：文件过大'
        solutionText =
          '上传的文件超出服务器处理限制，请尝试压缩或分割文件后再上传，或使用示例图像。'
      } else if (errorMsg.includes('磁盘空间不足')) {
        errorTitle = '诊断失败：服务器存储空间不足'
        solutionText = '服务器存储空间已满，请联系管理员处理或使用示例图像。'
      } else if (errorMsg.includes('nnUNet')) {
        errorTitle = '诊断失败：模型处理错误'
        solutionText = '医学影像模型处理过程中出错，请检查文件完整性或使用示例图像。'
      }
      // 创建错误提示内容（无重试按钮）
      const errorHtml = `
                <div class="error-container" style="text-align:center;padding:50px 0;">
                    <div style="color:red;font-size:60px;margin-bottom:20px;">!</div>
                    <div style="font-size:18px;font-weight:bold;margin-bottom:10px;color:#333;">${errorTitle}</div>
                    <div style="color:#555;margin-bottom:15px;">${errorMsg}</div>
                    <div style="color:#666;margin-bottom:30px;font-size:14px;">${solutionText}</div>
                </div>
            `
      // 显示错误内容
      $('#resultSection').html(errorHtml).show()
      // 2秒后自动重置页面
      setTimeout(function () {
        resetModule()
      }, 2000)
      // 如果在iframe中，向父窗口发送错误信息
      if (isEmbedded) {
        try {
          window.parent.postMessage(
            {
              type: 'error',
              message: errorMsg,
              title: errorTitle,
              solution: solutionText,
            },
            '*'
          )
          // console.log('已发送错误信息到父窗口');
        } catch (e) {
          console.error('发送错误消息失败:', e)
        }
      }
    }

    // 绑定滑动条事件
    $('#sliceSlider').off('input').off('change')
    $('#sliceSlider').on('input', function () {
      currentSliceIndex = parseInt($(this).val())
      updateSliceControls()
    })
    $('#sliceSlider').on('change', function () {
      currentSliceIndex = parseInt($(this).val())
      updateSliceControls()
      loadSlice()
    })

    // 绑定视角选择事件
    $('input[name="dim"]').on('change', function () {
      loadSlice()
    })

    // 使用示例图像
    $('#demoBtn').on('click', function () {
      // 防止重复点击
      if (isProcessing) {
        // console.log('正在处理中，忽略重复点击');
        return
      }

      // 设置状态
      isProcessing = true
      usedDemoImage = true

      // 自动选择大脑器官（使用示例图像时）
      $('.organ-buttons button').removeClass('active')
      $('.organ-buttons button[data-organ="brain"]').addClass('active')
      selectedOrgan = '大脑'
      // console.log('示例模式：自动选择大脑器官');

      // 显示加载动画
      $('.loading-overlay').show()

      $.ajax({
        url: '/predict_demo',
        type: 'POST',
        success: function (response) {
          $('.loading-overlay').hide()
          isProcessing = false

          // 确保响应中包含必要的字段
          if (!response.img_shape) {
            response.img_shape = [256, 256, 256] // 默认尺寸
          }

          // 如果服务器返回了器官信息，确保它被传递到showResult函数
          if (response.organ) {
            selectedOrgan = response.organ
          } else {
            // 如果服务器没有返回器官信息，默认为大脑
            selectedOrgan = '大脑'
            response.organ = '大脑'
          }

          showResult(response)
        },
        error: function (xhr) {
          isProcessing = false
          let errorMsg = '诊断失败，请重试'
          if (xhr.responseJSON && xhr.responseJSON.error) {
            errorMsg = '诊断失败：' + xhr.responseJSON.error
          }
          handleError(errorMsg, xhr.status)
        },
      })
    })

    // 文件上传
    $('#uploadBtn').on('click', function () {
      // 防止重复点击
      if (isProcessing) {
        // console.log('正在处理中，忽略重复点击');
        return
      }

      // 检查是否已选择器官类型
      if (!selectedOrgan) {
        layer.msg('请先选择器官类型', { icon: 0 })
        // 高亮器官选择区域以引导用户
        $('.organ-buttons').addClass('highlight-section')
        setTimeout(function () {
          $('.organ-buttons').removeClass('highlight-section')
        }, 2000)
        return
      }

      // 重置示例图像标志
      usedDemoImage = false
      $('#fileInput').click()
    })
    // 文件选择变更事件
    $('#fileInput').on('change', function () {
      if (this.files && this.files[0]) {
        var fileName = this.files[0].name
        var fileSize = this.files[0].size / (1024 * 1024) // 转换为MB

        // 检查文件格式是否正确
        var isValidFile =
          fileName.toLowerCase().endsWith('.nii') || fileName.toLowerCase().endsWith('.nii.gz')

        if (!isValidFile) {
          // 显示错误提示
          $('#fileNameDisplay').html(
            '<span style="color: #ea4335;">错误：不支持的文件格式 - ' +
              fileName +
              '</span>' +
              '<div class="file-error">请选择 .nii 或 .nii.gz 格式的文件</div>'
          )

          // 弹出提示
          layer.msg('请上传 .nii 或 .nii.gz 格式的文件', { icon: 2 })
          return
        }

        // 显示文件信息
        $('#fileNameDisplay').html(
          '<span style="color: #1E9FFF;">已选择：' +
            fileName +
            '</span>' +
            '<div style="font-size:12px;color:#999;">文件大小：' +
            fileSize.toFixed(2) +
            ' MB</div>'
        )

        // 检查是否已选择器官
        if (!selectedOrgan) {
          // 没有选择器官，提醒用户选择
          layer.msg('请选择要分析的器官类型', { icon: 0 })
          // 高亮器官选择区域
          $('.organ-buttons').addClass('highlight-section')
          setTimeout(function () {
            $('.organ-buttons').removeClass('highlight-section')
          }, 2000)
        } else {
          // 已选择器官，询问是否开始分析
          const organName = selectedOrgan

          // 保存对话框索引，用于后续关闭
          var confirmIndex = layer.confirm(
            '是否使用已选择的器官类型（' + organName + '）进行分析？',
            {
              btn: ['开始分析', '取消'],
            },
            function (index) {
              // 用户点击"开始分析"，关闭对话框
              layer.close(index)

              // 开始分析处理
              startAnalysis(organName)
            }
          )
        }
      }
    })

    // 器官选择按钮点击事件
    $('.organ-buttons button')
      .hover(
        function () {
          $(this).addClass('layui-btn-hover')
        },
        function () {
          $(this).removeClass('layui-btn-hover')
        }
      )
      .on('click', function () {
        // 防止重复点击或处理中的点击
        if (isProcessing) {
          // console.log('正在处理中，忽略重复点击');
          return false
        }

        var taskId = $(this).data('task')
        var organName = $(this).data('organ')

        // 高亮选中的按钮
        $('.organ-buttons button').removeClass('active')
        $(this).addClass('active')

        // 更新选中的器官
        selectedOrgan = organName

        // 如果已经选择了文件，询问是否立即开始分析
        var fileInput = document.getElementById('fileInput')
        if (fileInput.files && fileInput.files.length > 0) {
          // 保存对话框索引，用于后续关闭
          var confirmIndex = layer.confirm(
            '是否使用选择的器官类型（' + organName + '）分析已上传的文件？',
            {
              btn: ['开始分析', '取消'],
            },
            function (index) {
              // 用户点击"开始分析"，关闭对话框
              layer.close(index)

              // 开始分析处理
              startAnalysis(organName)
            }
          )
        } else if (!usedDemoImage) {
          // 提示用户上传文件
          layer.msg('请点击"上传文件"按钮选择要分析的文件', { icon: 1 })
        }
      })

    // 统一的开始分析函数
    function startAnalysis(organName) {
      // 防止重复处理
      if (isProcessing) {
        // console.log('正在处理中，忽略重复请求');
        return
      }

      // 设置处理状态
      isProcessing = true

      // 查找对应的器官按钮并获取task_id
      var organButton = $(`.organ-buttons button[data-organ="${organName}"]`)
      if (!organButton.length) {
        layer.msg('未找到对应的器官按钮', { icon: 2 })
        isProcessing = false
        return
      }

      var taskId = organButton.data('task')

      // 检查是否有文件需要上传
      var fileInput = document.getElementById('fileInput')
      if (!usedDemoImage && (!fileInput.files || fileInput.files.length === 0)) {
        layer.msg('请先选择要上传的文件', { icon: 0 })
        isProcessing = false
        return
      }

      // 显示加载提示
      $('.loading-overlay').show()

      // 创建表单数据
      var formData = new FormData($('#uploadForm')[0])
      formData.append('task_id', taskId)
      formData.append('organ_name', organName)

      // 将从URL获取的患者ID添加到表单数据中
      if (patientIdFromUrl) {
        formData.append('patient_id', patientIdFromUrl)
      }

      // 执行AJAX请求
      $.ajax({
        url: '/predict',
        type: 'POST',
        data: formData,
        processData: false,
        contentType: false,
        timeout: 120000, // 2分钟超时，防止长时间无响应
        success: function (response) {
          $('.loading-overlay').hide()
          isProcessing = false

          if (response.success) {
            showResult({
              result: response.result,
              img_shape: response.img_shape || [256, 256, 256], // 默认尺寸
              organ: response.organ,
            })
          } else if (response.error) {
            handleError('诊断失败：' + response.error)
          }
        },
        error: function (xhr, textStatus, errorThrown) {
          // console.error('请求错误:', xhr.status, textStatus, errorThrown);
          $('.loading-overlay').hide()
          isProcessing = false

          let errorMsg = '诊断失败，请重试'
          if (xhr.responseJSON && xhr.responseJSON.error) {
            errorMsg = '诊断失败：' + xhr.responseJSON.error
          } else if (xhr.status === 413) {
            errorMsg = '诊断失败：文件太大，超出服务器处理限制'
          } else if (textStatus === 'timeout') {
            errorMsg = '诊断失败：请求超时，服务器处理时间过长'
          } else if (xhr.statusText) {
            errorMsg = '诊断失败：' + xhr.statusText
          }

          // 记录详细错误信息到控制台
          // console.log('错误状态码:', xhr.status);
          // console.log('错误文本:', xhr.statusText);
          // console.log('异常:', errorThrown);

          handleError(errorMsg, xhr.status)

          // 如果是在iframe中嵌入的，还需要向父窗口发送详细的错误信息
          if (isEmbedded) {
            try {
              window.parent.postMessage(
                {
                  type: 'error-details',
                  status: xhr.status,
                  statusText: xhr.statusText,
                  message: errorMsg,
                  technical: errorThrown || '未知错误',
                },
                '*'
              )
            } catch (e) {
              console.error('发送详细错误信息失败:', e)
            }
          }
        },
      })
    }

    // 发送动态高度到父窗口
    function sendResize() {
      if (window.isEmbedded) {
        var newHeight = document.documentElement.scrollHeight
        window.parent.postMessage({ type: 'setHeight', height: newHeight }, '*')
      }
    }

    // 显示预测结果及初始化切片查看
    function showResult(response) {
      // 显示诊断结果
      $('#resultText').html('<div style="font-weight: bold;">' + response.result + '</div>')

      // 如果response中包含器官信息，更新selectedOrgan变量
      if (response.organ) {
        selectedOrgan = response.organ
      }

      // 显示影像尺寸
      if (response.img_shape) {
        $('#imgShape').html('<div>影像尺寸：' + response.img_shape.join(' × ') + '</div>')

        // 根据影像尺寸设置最大切片数
        maxSliceCount = Math.max.apply(null, response.img_shape || [256, 256, 256]) - 1
        currentSliceIndex = Math.floor(maxSliceCount / 2)
        updateSliceControls()
      }

      // 显示结果和切片区域
      $('#resultSection, #sliceSection').fadeIn(500)

      // 动态调整 iframe 高度
      setTimeout(sendResize, 600)

      // 重新渲染表单控件
      form.render()

      // 加载初始切片
      loadSlice()

      // 滚动到结果区域
      $('html, body').animate(
        {
          scrollTop: $('#resultSection').offset().top - 20,
        },
        500
      )

      // 如果在iframe中，向父窗口发送诊断结果
      if (isEmbedded) {
        try {
          window.parent.postMessage(
            {
              type: 'diagnosis-result',
              result: {
                organ: selectedOrgan,
                result: response.result,
                imgShape: response.img_shape,
              },
            },
            '*'
          )
        } catch (e) {
          console.error('发送诊断结果失败:', e)
        }
      }

      // 如果响应中包含 imaging_id，则存储它
      if (response.imaging_id) {
        currentImagingId = response.imaging_id
        console.log('存储当前影像记录ID:', currentImagingId)
      }
    }

    // 保存切片的数组
    let savedSlices = []

    // 保存当前切片按钮
    $('#saveSliceBtn').on('click', function () {
      // 防止重复点击
      if (isProcessing) {
        // console.log('正在处理中，忽略重复点击');
        return
      }

      const currentImg = $('#sliceImageContainer img').attr('src')
      if (!currentImg) {
        layer.msg('请先选择视角和层数查看切片', { icon: 2 })
        return
      }

      const dim = lastViewDim
      const index = currentSliceIndex
      const viewName = ['X轴', 'Y轴', 'Z轴'][dim]

      const sliceData = {
        id: Date.now(),
        img: currentImg,
        dim: dim,
        index: index,
        viewName: viewName,
      }

      // 前端防重复保存
      if (!savedSlices.some(s => s.dim === sliceData.dim && s.index === sliceData.index)) {
        // 设置处理状态
        isProcessing = true

        // 显示加载动画
        layer.load(1, { shade: [0.1, '#fff'] })

        // 保存到前端数组
        savedSlices.push(sliceData)

        // 发送给后端
        $.ajax({
          url: '/save_slice',
          type: 'POST',
          contentType: 'application/json',
          data: JSON.stringify(sliceData),
          success: function (res) {
            layer.closeAll('loading')
            isProcessing = false

            renderSavedSlices()
            $('#savedSlicesContainer').fadeIn()

            layer.msg('切片保存成功', { icon: 1 })
          },
          error: function (xhr) {
            layer.closeAll('loading')
            isProcessing = false

            // 仍然在前端显示
            renderSavedSlices()
            $('#savedSlicesContainer').fadeIn()

            layer.msg('切片已在前端保存，但保存到服务器失败', { icon: 0 })
          },
        })
      } else {
        layer.msg('该切片已保存', { icon: 2 })
      }
    })

    // 渲染已保存切片
    function renderSavedSlices() {
      const container = $('#savedSlicesGrid').empty()

      if (savedSlices.length === 0) {
        container.html(
          '<div class="layui-text" style="color:#999;text-align:center;padding:20px;">暂无保存的切片</div>'
        )
        return
      }

      savedSlices.forEach(slice => {
        container.append(`
                    <div class="saved-slice">
                        <img src="${slice.img}" alt="保存的切片" onclick="this.classList.toggle('zoom')">
                        <div class="delete-btn" onclick="deleteSlice(${slice.id})">×</div>
                        <div class="slice-info">
                            ${slice.viewName} 层${slice.index}
                        </div>
                    </div>
                `)
      })
    }

    // 删除切片功能
    window.deleteSlice = function (id) {
      layer.confirm('确定要删除这个切片吗？', { icon: 3, title: '提示' }, function (index) {
        savedSlices = savedSlices.filter(s => s.id !== id)
        renderSavedSlices()

        if (savedSlices.length === 0) {
          $('#savedSlicesContainer').fadeOut()
        }

        layer.close(index)
      })
    }

    // 添加双击放大切片功能
    $(document).on('dblclick', '#sliceImageContainer img', function () {
      var src = $(this).attr('src')
      layer.photos({
        photos: {
          title: '查看切片',
          data: [
            {
              src: src,
            },
          ],
        },
        anim: 5,
      })
    })

    // 监听来自父窗口的消息
    if (isEmbedded) {
      window.addEventListener('message', function (event) {
        // console.log('收到父窗口消息:', event.data);

        // 处理父窗口发来的iframe-loaded消息
        if (event.data === 'iframe-loaded') {
          // console.log('收到iframe-loaded消息，回复ready状态');
          try {
            window.parent.postMessage('predict-module-ready', '*')
          } catch (e) {
            console.error('回复父窗口失败:', e)
          }
          return
        }

        // 处理父窗口发来的命令
        if (typeof event.data === 'object') {
          const message = event.data

          // 初始化数据
          if (message.type === 'init') {
            // console.log('收到初始化数据:', message.data);
            if (message.data.defaultOrgan) {
              // 存储默认器官但不立即点击
              const defaultOrgan = message.data.defaultOrgan

              // 仅高亮显示默认器官按钮，但不触发点击事件
              const organButton = $(`.organ-buttons button[data-organ="${defaultOrgan}"]`)
              if (organButton.length) {
                // 只进行高亮显示，不执行点击
                $('.organ-buttons button').removeClass('active')
                organButton.addClass('active')
                selectedOrgan = defaultOrgan
                // console.log('已高亮默认器官:', defaultOrgan);

                // 创建弱提示，告知用户选择文件
                setTimeout(() => {
                  layer.msg('请上传.nii或.nii.gz格式的文件，或使用示例图像', {
                    icon: 6,
                    time: 4000,
                  })
                }, 1500)
              }
            }
          }

          // 命令处理
          else if (message.type === 'command') {
            // console.log('收到命令:', message.action);

            switch (message.action) {
              case 'reset':
                // 重置页面状态
                resetModule()
                // console.log('已重置预测模块');
                break

              case 'selectOrgan':
                // 选择器官
                if (message.data && message.data.organ) {
                  const organButton = $(`.organ-buttons button[data-organ="${message.data.organ}"]`)
                  if (organButton.length) {
                    organButton.click()
                    // console.log('已选择器官:', message.data.organ);
                  } else {
                    console.warn('找不到器官按钮:', message.data.organ)
                  }
                }
                break

              case 'viewSlice':
                // 从父窗口接收查看切片命令
                if (
                  message.data &&
                  typeof message.data.dim !== 'undefined' &&
                  typeof message.data.index !== 'undefined'
                ) {
                  // console.log('接收到切片查看请求:', message.data);
                  // 设置维度单选按钮
                  $(`input[name="dim"][value="${message.data.dim}"]`).prop('checked', true)
                  // 设置索引值
                  $('#sliceIndex').val(message.data.index)
                  // 触发查看切片
                  $('#viewSliceBtn').click()
                }
                break

              case 'saveSlice':
                // 保存当前切片
                $('#saveSliceBtn').click()
                break
            }
          }
        }
      })
    }

    // 生成报告按钮
    $('#generateReportBtn').on('click', function () {
      if (isProcessing) return
      var diagnosisInfo = $('#resultText').text()
      if (!diagnosisInfo) {
        layer.msg('诊断信息为空，无法生成报告', { icon: 2 })
        return
      }

      isProcessing = true
      layer.load(1, { shade: [0.1, '#fff'] })

      $.ajax({
        url: '/generate_report',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
          diagnosis_info: diagnosisInfo,
          imaging_id: currentImagingId, // 发送存储的影像ID
        }),
        success: function (res) {
          layer.closeAll('loading')
          isProcessing = false
          if (res.report) {
            var reportData = res.report

            // 显示患者关联信息（如果有）
            var titleExtra = res.patient_id ? ' - 已关联到患者ID: ' + res.patient_id : ''
            if (res.saved) {
              titleExtra += ' (报告已保存)'
            }

            layer.open({
              type: 1,
              title:
                '<i class="layui-icon layui-icon-note" style="color:#1E9FFF;margin-right:8px;"></i>生成的医疗报告' +
                titleExtra,
              area: ['600px', '400px'],
              shade: 0.2,
              shadeClose: true,
              resize: true,
              move: true,
              content:
                '<div id="reportContent" style="padding:24px; background:#f8fafc; border-radius:10px; box-shadow:0 2px 12px rgba(30,159,255,0.08); max-height:300px; overflow-y:auto; font-size:16px; color:#222; line-height:1.8;">' +
                reportData.replace(/\\n/g, '<br>') +
                '</div>',
              btn: [
                '<span style="color:#fff;background:#1E9FFF;padding:6px 18px;border-radius:4px;">下载报告</span>',
                '<span style="color:#666;">关闭</span>',
              ],
              yes: function (index, layero) {
                var blob = new Blob([reportData.replace(/<br>/g, '\\n')], {
                  type: 'text/plain;charset=utf-8',
                })
                var link = document.createElement('a')
                link.href = URL.createObjectURL(blob)
                link.download = 'medical_report.txt'
                document.body.appendChild(link)
                link.click()
                document.body.removeChild(link)
              },
              btn2: function (index, layero) {
                layer.close(index)
              },
            })
          } else {
            layer.msg(res.message || '报告生成失败', { icon: 2 })
          }
        },
        error: function (xhr) {
          layer.closeAll('loading')
          isProcessing = false
          layer.msg('请求报告生成失败', { icon: 2 })
        },
      })
    })
  })
}

// 在文档加载完成后初始化预测模块
document.addEventListener('DOMContentLoaded', function () {
  console.log('predict.js 加载完成，初始化预测模块')
  // 确保jQuery已加载
  if (typeof jQuery === 'undefined') {
    console.error('jQuery 未加载，无法初始化预测模块')
    return
  }

  // 初始化预测模块
  initPredictModule()
})
