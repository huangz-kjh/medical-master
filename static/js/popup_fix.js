
$(document).ready(function() {
    $('.view-appointments-btn, .change-status-btn').each(function() {
        var btnId = $(this).data('id');
        if (!btnId || btnId === 'undefined') {
            $(this).prop('disabled', true)
                  .css('opacity', '0.5')
                  .attr('title', '无效的ID')
                  .off('click');
        }
    });
    var originalShowPatientAppts = window.showPatientAppointments;
    window.showPatientAppointments = function(patientId, patientName) {
        if (!patientId || patientId === "undefined" || patientId === undefined) {
            layui.use(['layer'], function() {
                var layer = layui.layer;
                layer.msg('无效的患者ID', {icon: 2});
            });
            return;
        }
        if (typeof originalShowPatientAppts === 'function') {
            originalShowPatientAppts(patientId, patientName);
        }
    };
    var originalViewAppointment = window.viewAppointmentDetail;
    window.viewAppointmentDetail = function(appointmentId) {
        if (!appointmentId || appointmentId === "undefined" || appointmentId === undefined) {
            layui.use(['layer'], function() {
                var layer = layui.layer;
                layer.msg('无效的预约ID', {icon: 2});
            });
            return;
        }
        if (typeof originalViewAppointment === 'function') {
            originalViewAppointment(appointmentId);
        }
    };
    var originalChangeStatus = window.showChangeStatusDialog;
    window.showChangeStatusDialog = function(appointmentId) {
        if (!appointmentId || appointmentId === "undefined" || appointmentId === undefined) {
            layui.use(['layer'], function() {
                var layer = layui.layer;
                layer.msg('无效的预约ID', {icon: 2});
            });
            return;
        }
        if (typeof originalChangeStatus === 'function') {
            originalChangeStatus(appointmentId);
        }
    };
    var originalChangePatientStatus = window.showChangePatientStatus;
    window.showChangePatientStatus = function(patientId, patientName, currentStatus) {
        if (!patientId || patientId === "undefined" || patientId === undefined) {
            layui.use(['layer'], function() {
                var layer = layui.layer;
                layer.msg('无效的患者ID', {icon: 2});
            });
            return;
        }
        if (typeof originalChangePatientStatus === 'function') {
            originalChangePatientStatus(patientId, patientName, currentStatus);
        }
    };
    $(document).on('click', '.view-detail-btn, .confirm-appointment-btn, .reject-appointment-btn, .complete-appointment-btn, .cancel-appointment-btn', function(e) {
        var id = $(this).data('id');
        if (!id || id === 'undefined' || id === undefined) {
            e.preventDefault();
            e.stopPropagation();
            layui.use(['layer'], function() {
                var layer = layui.layer;
                layer.msg('无效的ID，无法执行操作', {icon: 2});
            });
            return false;
        }
    });
    var originalOpen = layer.open;
    if (typeof originalOpen === 'function') {
        layer.open = function(options) {
            var originalSuccess = options.success;
            options.success = function(layero, index) {
                if (layero && layero.length) {
                    $(layero).find('.layui-layer-content').css({
                        'max-height': '500px',
                        'overflow-y': 'auto'
                    });
                    setTimeout(function() {
                        layer.style(index, {
                            width: options.area && options.area[0] ? options.area[0] : '600px'
                        });
                    }, 10);
                }
                if (typeof originalSuccess === 'function') {
                    originalSuccess(layero, index);
                }
            };
            return originalOpen.call(layer, options);
        };
    }
}); 