document.addEventListener('DOMContentLoaded', function () {
    // 处理表单提交
    document.body.addEventListener('submit', function (e) {
        const form = e.target;
        // 检查是否是患者相关表单
        if (form.id === 'patientForm' || form.action.includes('/patients/')) {
            e.preventDefault();

            // 表单验证
            if (!form.checkValidity()) {
                e.stopPropagation();
                form.classList.add('was-validated');
                return;
            }

            const formData = new FormData(form);

            fetch(form.action, {
                method: 'POST',
                body: formData
            })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        // 使用SweetAlert2显示成功消息
                        Swal.fire({
                            title: '成功',
                            text: data.message,
                            icon: 'success',
                            confirmButtonText: '确定'
                        }).then((result) => {
                            if (result.isConfirmed && data.redirect) {
                                window.location.href = data.redirect;
                            }
                        });
                    } else {
                        Swal.fire({
                            title: '错误',
                            text: data.message,
                            icon: 'error',
                            confirmButtonText: '确定'
                        });
                    }
                })
                .catch(error => {
                    Swal.fire({
                        title: '错误',
                        text: '提交表单时发生错误',
                        icon: 'error',
                        confirmButtonText: '确定'
                    });
                    console.error('Error:', error);
                });
        }
    });

    // 处理删除患者按钮点击
    document.body.addEventListener('click', function(e) {
        const deletePatientBtn = e.target.closest('.delete-patient');
        if (deletePatientBtn) {
            e.preventDefault();
            const patientId = deletePatientBtn.dataset.patientId;
            handleDelete(patientId);
        }

        const deleteReportBtn = e.target.closest('.delete-report');
        if (deleteReportBtn) {
            e.preventDefault();
            const reportId = deleteReportBtn.dataset.reportId;
            handleDeleteReport(reportId);
        }
    });
});

// 显示提示弹窗
function showAlert(message, type = 'success') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed top-0 start-50 translate-middle-x mt-3`;
    alertDiv.style.zIndex = '9999';
    alertDiv.innerHTML = `
      ${message}
      <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
  `;
    document.body.appendChild(alertDiv);

    // 3秒后自动关闭
    setTimeout(() => {
        alertDiv.remove();
    }, 3000);
}

// 处理删除操作
function handleDelete(patientId) {
    if (confirm('确认删除该患者吗？此操作将删除所有相关记录且无法恢复！')) {
        fetch(`/patients/${patientId}/delete`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    showAlert(data.message, 'success');
                    setTimeout(() => {
                        window.location.href = data.redirect;
                    }, 1500);
                } else {
                    showAlert(data.message, 'danger');
                }
            })
            .catch(error => {
                showAlert('删除操作失败，请重试', 'danger');
                console.error('Error:', error);
            });
    }
}

// 处理编辑操作
function handleEdit(patientId) {
    const form = document.getElementById('editForm');
    const formData = new FormData(form);

    fetch(`/patients/${patientId}/edit`, {
        method: 'POST',
        body: formData
    })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                showAlert(data.message, 'success');
                setTimeout(() => {
                    window.location.href = data.redirect;
                }, 1500);
            } else {
                showAlert(data.message, 'danger');
            }
        })
        .catch(error => {
            showAlert('更新操作失败，请重试', 'danger');
            console.error('Error:', error);
        });
}

// 处理删除分析报告
function handleDeleteReport(reportId) {
    if (confirm('确认删除该分析报告吗？此操作不可恢复！')) {
        fetch(`/patients/${parseInt(reportId)}/delete-report`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    showAlert(data.message, 'success');
                    setTimeout(() => {
                        window.location.reload();
                    }, 1500);
                } else {
                    showAlert(data.message, 'danger');
                }
            })
            .catch(error => {
                showAlert('删除操作失败，请重试', 'danger');
                console.error('Error:', error);
            });
    }
}