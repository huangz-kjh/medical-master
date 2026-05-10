$(document).ready(function () {
    // 加载用户信息
    loadUserProfile();

    // 检查是否为患者角色并相应显示/隐藏字段
    checkUserRole();

    // 更新个人资料按钮点击事件
    $("#update-profile-btn").click(function () {
        // 先处理紧急联系人字段
        const name = $("#emergency_name").val().trim();
        const phone = $("#emergency_phone").val().trim();
        $("#emergency_contact").val(name && phone ? `${name}:${phone}` : "无");


        // 然后调用更新函数
        updateProfile();
    });

    // 更改密码按钮点击事件
    $("#change-password-btn").click(function () {
        changePassword();
    });
});

// 加载用户个人资料
function loadUserProfile() {
    $.ajax({
        url: '/get_user_profile',
        type: 'GET',
        success: function (response) {
            if (response.status === "success") {
                const user = response.data;

                // 顶部头像 & 角色
                $("#username-display").text(user.username || "未设置");
                $("#role-display").text(
                    user.role === 'patient' ? '患者' :
                        (user.role === 'doctor' ? '医生' : '管理员')
                );
                $("#avatar-initial").text((user.username || "U").charAt(0).toUpperCase());

                // 设置用户名、真实姓名和身份证号
                $("#username").val(user.username || "未设置");
                $("#real_name").val(user.real_name || "未设置");
                $("#id_card").val(user.id_card || "未设置");

                // 显示用户名、真实姓名和身份证号
                $("#username-display-field").text(user.username || "未设置");
                $("#real-name-display-field").text(user.real_name || "未设置");
                $("#id-card-display-field").text(user.id_card || "未设置");

                // 其他只读字段
                $("#reg-date-value").text(user.registration_date || "无");
                $("#last-login-value").text(user.last_login || "无");
                $("#account-status-value").html(
                    user.is_active
                        ? '<span class="badge bg-success">正常</span>'
                        : '<span class="badge bg-danger">已禁用</span>'
                );

                // 可编辑字段
                $("#email").val(user.email || "");
                $("#phone").val(user.phone || "");
                $("#address").val(user.address || "");

                if (user.role === 'patient') {
                    if (user.emergency_contact && user.emergency_contact !== "无") {
                        const [name, phone] = user.emergency_contact.split(":");
                        $("#emergency_name").val(name ? name.trim() : "");
                        $("#emergency_phone").val(phone ? phone.trim() : "");
                        $("#emergency_contact").val(user.emergency_contact);
                    } else {
                        $("#emergency_name").val("");
                        $("#emergency_phone").val("");
                        $("#emergency_contact").val("无");
                    }
                    $(".patient-only-fields").show();
                } else {
                    $(".patient-only-fields").hide();
                }
            } else {
                console.error("加载用户资料失败:", response.message);
            }
        },
        error: function (error) {
            console.error("请求失败:", error);
        }
    });
}

// 检查用户角色
function checkUserRole() {
    $.ajax({
        url: '/get_user_role',
        type: 'GET',
        success: function (response) {
            if (response.status === "success") {
                if (response.role === 'patient') {
                    $(".patient-only-fields").show();
                } else {
                    $(".patient-only-fields").hide();
                }
            }
        }
    });
}

// 更新个人资料
function updateProfile() {
    const formData = new FormData(document.getElementById('profileForm'));
    $.ajax({
        url: '/update_profile',
        type: 'POST',
        data: formData,
        processData: false,
        contentType: false,
        success: function (response) {
            if (response.status === "success") {
                $("#profile-success-alert").text(response.message).show();
                setTimeout(function () {
                    $("#profile-success-alert").hide();
                }, 3000);
            } else {
                $("#profile-error-alert").text(response.message).show();
                setTimeout(function () {
                    $("#profile-error-alert").hide();
                }, 3000);
            }
        },
        error: function (error) {
            $("#profile-error-alert").text("请求失败，请稍后重试").show();
            setTimeout(function () {
                $("#profile-error-alert").hide();
            }, 3000);
        }
    });
}

// 修改密码
function changePassword() {
    const currentPassword = $("#current_password").val();
    const newPassword = $("#new_password").val();
    const confirmPassword = $("#confirm_password").val();

    // 前端验证
    if (newPassword.length < 6) {
        $("#password-error-alert").text("新密码长度不能少于6个字符").show();
        setTimeout(function () {
            $("#password-error-alert").hide();
        }, 3000);
        return;
    }

    if (newPassword !== confirmPassword) {
        $("#password-error-alert").text("两次输入的新密码不一致").show();
        setTimeout(function () {
            $("#password-error-alert").hide();
        }, 3000);
        return;
    }

    // 提交修改密码请求
    $.ajax({
        url: '/change_password',
        type: 'POST',
        data: {
            current_password: currentPassword,
            new_password: newPassword,
            confirm_password: confirmPassword
        },
        success: function (response) {
            if (response.status === "success") {
                $("#password-success-alert").text(response.message).show();
                $("#passwordForm")[0].reset();
                setTimeout(function () {
                    $("#password-success-alert").hide();
                    if (response.redirect) {
                        window.location.href = response.redirect;
                    }
                }, 1000);
            } else {
                $("#password-error-alert").text(response.message).show();
                setTimeout(function () {
                    $("#password-error-alert").hide();
                }, 3000);
            }
        },
        error: function (error) {
            $("#password-error-alert").text("请求失败，请稍后重试").show();
            setTimeout(function () {
                $("#password-error-alert").hide();
            }, 3000);
        }
    });
}