layui.use(['form', 'layer'], function () {
    var form = layui.form;
    var layer = layui.layer;
    // 标记用户名和身份证是否可用
    var isUsernameAvailable = false;
    var isIdCardAvailable = false;

    // 粒子背景效果
    $(document).ready(function () {
        $('.layui-container').particleground({
            dotColor: '#7ec7fd',
            lineColor: '#7ec7fd',
            density: 10000
        });
    });

    // 自定义表单验证规则
    form.verify({
        username: function (value) {
            if (value.length < 2) {
                return '用户名至少2个字符';
            }
            if (!isUsernameAvailable) {
                return '请确保用户名可用';
            }
        },
        password: [
            /^[\S]{6,12}$/,
            '密码必须6到12位，且不能出现空格'
        ],
        identity: [
            /(^\d{15}$)|(^\d{18}$)|(^\d{17}(\d|X|x)$)/,
            '请输入正确的身份证号'
        ],
        phone: [
            /^1[3-9]\d{9}$/,
            '请输入正确的手机号'
        ],
        emergency_phone: function(value) {
            if (value && !/^1[3-9]\d{9}$/.test(value)) {
                return '请输入正确的紧急联系人电话';
            }
        }
    });

    // 用户名验证：延迟执行，避免频繁请求
    var usernameTimer;
    $('#username').on('input', function () {
        var username = $(this).val().trim();
        
        // 清除之前的延时器
        clearTimeout(usernameTimer);
        
        // 重置验证状态
        isUsernameAvailable = false;
        
        // 设置输入中的样式
        $('#username-check').attr('class', '').html('<i class="layui-icon layui-icon-loading layui-anim layui-anim-rotate layui-anim-loop"></i> 检查中...');
        
        // 设置新的延时器，延迟500毫秒执行
        usernameTimer = setTimeout(function() {
            checkUsername(username);
        }, 500);
    });
    
    // 用户名失去焦点时验证
    $('#username').on('blur', function () {
        var username = $(this).val().trim();
        if (username) {
            // 立即执行验证，无需延迟
            clearTimeout(usernameTimer);
            checkUsername(username);
        } else {
            $('#username-check').attr('class', 'error-text').text('用户名不能为空');
        }
    });
    
    // 检查用户名函数
    function checkUsername(username) {
        if (!username) {
            $('#username-check').attr('class', 'error-text').text('用户名不能为空');
            return;
        }
        
        if (username.length < 2) {
            $('#username-check').attr('class', 'error-text').text('用户名至少2个字符');
            return;
        }
        
        if (!/^[a-zA-Z0-9_]+$/.test(username)) {
            $('#username-check').attr('class', 'error-text').text('用户名只能包含字母、数字和下划线');
            return;
        }
        
        $.ajax({
            url: '/check_username',
            type: 'POST',
            data: {username: username},
            success: function (res) {
                if (res.available) {
                    isUsernameAvailable = true;
                    $('#username-check').attr('class', 'success-text').html('<i class="layui-icon layui-icon-ok-circle"></i> ' + res.message);
                    $('#username').css('border-color', '#009688');
                } else {
                    isUsernameAvailable = false;
                    $('#username-check').attr('class', 'error-text').html('<i class="layui-icon layui-icon-close-fill"></i> ' + res.message);
                    $('#username').css('border-color', '#FF5722');
                }
            },
            error: function() {
                $('#username-check').attr('class', 'error-text').text('验证失败，请重试');
            }
        });
    }

    // 身份证号验证：延迟执行，避免频繁请求
    var idCardTimer;
    $('#id_card').on('input', function () {
        var id_card = $(this).val().trim();
        
        // 清除之前的延时器
        clearTimeout(idCardTimer);
        
        // 重置验证状态
        isIdCardAvailable = false;
        
        // 如果输入长度超过15位，设置输入中的样式
        if (id_card.length >= 15) {
            $('#id-check').attr('class', '').html('<i class="layui-icon layui-icon-loading layui-anim layui-anim-rotate layui-anim-loop"></i> 检查中...');
            
            // 设置新的延时器，延迟500毫秒执行
            idCardTimer = setTimeout(function() {
                checkIdCard(id_card);
            }, 500);
        } else {
            $('#id-check').attr('class', '').text('');
        }
    });
    
    // 身份证号失去焦点时验证
    $('#id_card').on('blur', function () {
        var id_card = $(this).val().trim();
        if (id_card) {
            // 立即执行验证，无需延迟
            clearTimeout(idCardTimer);
            checkIdCard(id_card);
        } else {
            $('#id-check').attr('class', 'error-text').text('身份证号不能为空');
        }
    });
    
    // 检查身份证号函数
    function checkIdCard(id_card) {
        if (!id_card) {
            $('#id-check').attr('class', 'error-text').text('身份证号不能为空');
            return;
        }
        
        if (!/^(\d{15}|\d{18}|\d{17}(\d|X|x))$/.test(id_card)) {
            $('#id-check').attr('class', 'error-text').text('身份证号格式不正确');
            return;
        }
        
        $.ajax({
            url: '/check_id_card',
            type: 'POST',
            data: {id_card: id_card},
            success: function (res) {
                if (res.available) {
                    isIdCardAvailable = true;
                    $('#id-check').attr('class', 'success-text').html('<i class="layui-icon layui-icon-ok-circle"></i> ' + res.message);
                    $('#id_card').css('border-color', '#009688');
                } else {
                    isIdCardAvailable = false;
                    $('#id-check').attr('class', 'error-text').html('<i class="layui-icon layui-icon-close-fill"></i> ' + res.message);
                    $('#id_card').css('border-color', '#FF5722');
                }
            },
            error: function() {
                $('#id-check').attr('class', 'error-text').text('验证失败，请重试');
            }
        });
    }

    // 密码确认验证
    $('#confirm_password').on('blur', function () {
        var password = $('#password').val();
        var confirmPassword = $(this).val();
        
        if (!confirmPassword) {
            return;
        }
        
        if (confirmPassword !== password) {
            layer.msg('两次输入的密码不一致', {icon: 5});
            $(this).css('border-color', '#FF5722');
        } else {
            $(this).css('border-color', '#009688');
        }
    });

    // 表单提交
    form.on('submit(register)', function (data) {
        // 密码确认验证
        if (data.field.password !== data.field.confirm_password) {
            layer.msg('两次输入的密码不一致', {icon: 5});
            return false;
        }
        
        // 验证用户名和身份证号是否通过检查
        if (!isUsernameAvailable) {
            layer.msg('请确保用户名可用', {icon: 2});
            return false;
        }
        
        if (!isIdCardAvailable && data.field.id_card) {
            layer.msg('请确保身份证号可用', {icon: 2});
            return false;
        }

        // 处理紧急联系人信息
        var emergency_name = $('#emergency_contact_name').val().trim();
        var emergency_phone = $('#emergency_contact_phone').val().trim();
        
        if ((emergency_name && !emergency_phone) || (!emergency_name && emergency_phone)) {
            layer.msg('请完整填写紧急联系人信息');
            return false;
        }

        // 显示加载中提示
        var loadIndex = layer.load(2, {shade: [0.3, '#333']});

        // 使用Ajax提交表单
        $.ajax({
            url: '/register',
            type: 'POST',
            data: data.field,
            success: function (res) {
                layer.close(loadIndex);
                if (res.status === 'success') {
                    layer.msg(res.message, {icon: 1, time: 2000}, function () {
                        window.location.href = res.redirect;
                    });
                } else {
                    // 提取错误信息中的关键部分
                    let errorMessage = res.message;
                    if (errorMessage.includes('Data truncated')) {
                        errorMessage = '血型信息格式不正确，请重新选择';
                    }
                    $('#errorMsg').show().find('.error-text').text(errorMessage);
                    layer.msg(errorMessage, {icon: 2});
                }
            },
            error: function (xhr) {
                layer.close(loadIndex);
                let errorMessage = '注册失败，请稍后重试';
                if (xhr.responseJSON && xhr.responseJSON.message) {
                    errorMessage = xhr.responseJSON.message;
                    if (errorMessage.includes('Data truncated')) {
                        errorMessage = '血型信息格式不正确，请重新选择';
                    }
                }
                $('#errorMsg').show().find('.error-text').text(errorMessage);
                layer.msg(errorMessage, {icon: 2});
            }
        });
        return false; // 阻止表单默认提交
    });
});