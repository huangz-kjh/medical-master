document.addEventListener('DOMContentLoaded', function() {
    const reportDetailModal = new bootstrap.Modal(document.getElementById('reportDetailModal'));
    let analyzeReportModal;
    
    // 根据用户角色初始化特定功能
    if (USER_ROLE === 'doctor') {
        analyzeReportModal = new bootstrap.Modal(document.getElementById('analyzeReportModal'));
    }
    
    // 查看报告详情
    const viewReportBtns = document.querySelectorAll('.view-report-btn');
    viewReportBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const reportId = this.getAttribute('data-id');
            loadReportDetails(reportId);
            reportDetailModal.show();
        });
    });
    
    // 加载报告详情
    function loadReportDetails(reportId) {
        document.getElementById('reportDetail').innerHTML = `
            <div class="text-center p-4">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-2 text-muted">加载报告数据中...</p>
            </div>
        `;
        
        fetch(`/api/reports/${reportId}`)
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    const report = data.report;
                    
                    // 检查是否有结论，如果没有则表示报告未完成分析
                    const isComplete = report.conclusion ? true : false;
                    const currentRole = USER_ROLE;
                    
                    // 构建报告详情的HTML
                    let detailHTML = `
                        <div class="report-header">
                            <div class="report-header-left">
                                <div class="report-title">${report.report_type}</div>
                                <div class="report-meta">
                                    <div class="report-meta-item">
                                        <i class="far fa-calendar-alt"></i>
                                        <span>检查日期: ${report.report_date}</span>
                                    </div>
                                    <div class="report-meta-item">
                                        <i class="far fa-clock"></i>
                                        <span>创建时间: ${report.created_at}</span>
                                    </div>
                                    <div class="report-meta-item">
                                        <i class="fas fa-tag"></i>
                                        <span>状态: ${isComplete ? '<span class="status-badge status-completed"><i class="fas fa-check-circle"></i> 已完成</span>' : '<span class="status-badge status-pending"><i class="fas fa-hourglass-half"></i> 待分析</span>'}</span>
                                    </div>
                                </div>
                            </div>
                            <div class="report-header-right">
                                <div class="report-patient">
                                    <div class="report-patient-name">
                                        <i class="fas fa-user-injured me-1"></i> 患者: ${report.patient_name}
                                    </div>
                                    <div class="report-patient-info">
                                        <a href="/patient/${report.patient_id}" class="btn btn-sm btn-outline-primary mt-2">
                                            <i class="fas fa-folder-open me-1"></i> 查看患者档案
                                        </a>
                                    </div>
                                </div>
                            </div>
                        </div>
                    `;
                    
                    // 如果有分析结果，添加到报告详情中
                    if (report.analysis_result) {
                        detailHTML += `
                            <div class="report-content">
                                <div class="report-section">
                                    <div class="report-section-title">
                                        <i class="fas fa-microscope me-1"></i> 分析结果
                                    </div>
                                    <div class="report-section-content">
                                        ${report.analysis_result.replace(/\n/g, '<br>')}
                                    </div>
                                </div>
                        `;
                    }
                    
                    // 如果有检查图像，添加到报告详情中
                    if (report.source_image_url) {
                        detailHTML += `
                            <div class="report-image">
                                <img src="${report.source_image_url}" alt="检查图像">
                            </div>
                        `;
                    }
                    
                    // 如果有结论，添加到报告详情中
                    if (report.conclusion) {
                        detailHTML += `
                            <div class="report-conclusion">
                                <div class="report-conclusion-title">
                                    <i class="fas fa-clipboard-check me-1"></i> 结论和建议
                                </div>
                                <div class="report-conclusion-content">
                                    ${report.conclusion.replace(/\n/g, '<br>')}
                                </div>
                            </div>
                        `;
                    }
                    
                    // 如果有健康建议，添加到报告详情中
                    if (report.health_advice) {
                        detailHTML += `
                            <div class="report-health-advice">
                                <div class="report-health-advice-title">
                                    <i class="fas fa-heartbeat me-1"></i> 健康建议
                                </div>
                                <div class="report-health-advice-content">
                                    ${report.health_advice.replace(/\n/g, '<br>')}
                                </div>
                            </div>
                        `;
                    }
                    
                    // 如果报告尚未完成分析，并且当前用户是医生，显示提示
                    if (!isComplete && currentRole === 'doctor') {
                        detailHTML += `
                            <div class="alert alert-info mt-4">
                                <i class="fas fa-info-circle me-2"></i> 此报告尚未完成分析。点击"分析"按钮添加分析结果和诊断结论。
                            </div>
                        `;
                    }
                    
                    // 关闭报告内容的div
                    if (report.analysis_result) {
                        detailHTML += `</div>`;
                    }
                    
                    document.getElementById('reportDetail').innerHTML = detailHTML;
                    
                    // 设置编辑按钮数据
                    if (USER_ROLE === 'doctor') {
                        document.getElementById('editReportBtn').setAttribute('data-id', report.report_id);
                        document.getElementById('printReportBtn').setAttribute('data-id', report.report_id);
                    }
                    
                } else {
                    document.getElementById('reportDetail').innerHTML = `
                        <div class="alert alert-danger">
                            <i class="fas fa-exclamation-circle me-2"></i> ${data.message || '加载报告详情失败'}
                        </div>
                    `;
                }
            })
            .catch(error => {
                console.error('Error:', error);
                document.getElementById('reportDetail').innerHTML = `
                    <div class="alert alert-danger">
                        <i class="fas fa-exclamation-circle me-2"></i> 加载报告详情时发生错误，请重试
                    </div>
                `;
            });
    }
    
    // 医生特有的功能
    if (USER_ROLE === 'doctor') {
        // 分析报告
        const analyzeReportBtns = document.querySelectorAll('.analyze-report-btn');
        analyzeReportBtns.forEach(btn => {
            btn.addEventListener('click', function() {
                const reportId = this.getAttribute('data-id');
                document.getElementById('reportId').value = reportId;
                
                // 清空表单
                document.getElementById('analysisResult').value = '';
                document.getElementById('conclusion').value = '';
                document.getElementById('healthAdvice').value = '';
                
                analyzeReportModal.show();
            });
        });
        
        // 保存分析结果
        document.getElementById('saveAnalysisBtn').addEventListener('click', function() {
            const reportId = document.getElementById('reportId').value;
            const analysisResult = document.getElementById('analysisResult').value;
            const conclusion = document.getElementById('conclusion').value;
            const healthAdvice = document.getElementById('healthAdvice').value;
            
            if (!analysisResult || !conclusion) {
                alert('请填写分析结果和结论');
                return;
            }
            
            // 显示加载状态
            const originalText = this.innerHTML;
            this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 保存中...';
            this.disabled = true;
            
            fetch(`/api/reports/${reportId}/analyze`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    analysis_result: analysisResult,
                    conclusion: conclusion,
                    health_advice: healthAdvice
                }),
            })
            .then(response => response.json())
            .then(data => {
                this.innerHTML = originalText;
                this.disabled = false;
                
                if (data.status === 'success') {
                    alert('报告分析已保存');
                    analyzeReportModal.hide();
                    window.location.reload(); // 重新加载页面
                } else {
                    alert(data.message || '保存分析失败');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('保存分析时发生错误，请重试');
                this.innerHTML = originalText;
                this.disabled = false;
            });
        });
        
        // 编辑报告按钮
        document.getElementById('editReportBtn').addEventListener('click', function() {
            const reportId = this.getAttribute('data-id');
            reportDetailModal.hide();
            
            // 加载报告数据到分析表单
            fetch(`/api/reports/${reportId}`)
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        const report = data.report;
                        
                        document.getElementById('reportId').value = reportId;
                        document.getElementById('analysisResult').value = report.analysis_result || '';
                        document.getElementById('conclusion').value = report.conclusion || '';
                        document.getElementById('healthAdvice').value = report.health_advice || '';
                        
                        analyzeReportModal.show();
                    } else {
                        alert(data.message || '加载报告数据失败');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('加载报告数据时发生错误，请重试');
                });
        });
        
        // 打印报告按钮
        document.getElementById('printReportBtn').addEventListener('click', function() {
            const reportId = this.getAttribute('data-id');
            window.open(`/reports/print/${reportId}`, '_blank');
        });
    }
}); 