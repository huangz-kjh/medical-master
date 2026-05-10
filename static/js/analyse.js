    // === 示例数据定义 ===
    const sampleData = {
        total_patients: 350,
        total_ct_scans: 280,
        total_medications: 420,
        total_assessments: 310,
        recent_patients: 45,
        gender_distribution: { '男': 200, '女': 150 },
        age_groups: { '0-18': 20, '19-35': 80, '36-50': 100, '51-65': 90, '66+': 60 },
        status_counts: { '住院': 120, '门诊': 180, '观察': 50 },
        blood_types: { 'A': 100, 'B': 90, 'AB': 40, 'O': 120 },
        ct_types: { '常规': 150, '增强': 100, '3D': 30 },  // 注意逗号
        cognitive_scores: {
            '正常 (27-30)': 140,
            '轻度障碍 (21-26)': 100,
            '中度障碍 (11-20)': 80,
            '重度障碍 (0-10)': 30
        },
        brain_condition_counts: {
            '脑萎缩': 120,
            '脑出血': 60,
            '脑梗塞': 80,
            '脑肿瘤': 30
        },
        medications: {
            '抗抑郁': 120,
            '镇痛': 90,
            '抗癫痫': 60,
            '抗焦虑': 80
        },
        anxiety_levels: {
            '1': 5, '2': 10, '3': 15, '4': 20, '5': 30,
            '6': 40, '7': 50, '8': 60, '9': 70, '10': 50
        },
        depression_levels: {
            '1': 8, '2': 12, '3': 18, '4': 25, '5': 35,
            '6': 45, '7': 55, '8': 65, '9': 75, '10': 60
        }
    };  // 结尾加分号

    // === 填充统计卡片 ===
    const statsInfo = [
        { icon: 'fa-user-injured', value: sampleData.total_patients, label: '总患者数' },
        { icon: 'fa-brain',         value: sampleData.total_ct_scans, label: 'CT扫描记录' },
        { icon: 'fa-pills',         value: sampleData.total_medications, label: '药物治疗记录' },
        { icon: 'fa-stethoscope',   value: sampleData.total_assessments, label: '神经系统评估' },
        { icon: 'fa-user-plus',     value: sampleData.recent_patients, label: '最近30天新患者' }
    ];
    const statsRow = document.getElementById('stats-row');
    statsInfo.forEach(item => {
        const col = document.createElement('div');
        col.className = 'col-md-3';
        col.innerHTML = `
            <div class="card stat-card">
                <div class="stat-icon"><i class="fas ${item.icon}"></i></div>
                <div class="stat-value">${item.value}</div>
                <div class="stat-label">${item.label}</div>
            </div>
        `;
        statsRow.appendChild(col);
    });

    // === 计算数据洞察 ===
    const ageTotal     = Object.values(sampleData.age_groups).reduce((a, b) => a + b, 0);
    const elderlyCount = sampleData.age_groups['51-65'] + sampleData.age_groups['66+'];
    document.getElementById('elderly-percentage').textContent =
        Math.round(elderlyCount / ageTotal * 100) + '%';

    const totalCog = Object.values(sampleData.cognitive_scores).reduce((a, b) => a + b, 0);
    const cogIssue = sampleData.cognitive_scores['轻度障碍 (21-26)']
                   + sampleData.cognitive_scores['中度障碍 (11-20)']
                   + sampleData.cognitive_scores['重度障碍 (0-10)'];
    document.getElementById('cognitive-issue-percentage').textContent =
        Math.round(cogIssue / totalCog * 100) + '%';

    const mainCond = Object.keys(sampleData.brain_condition_counts)
        .reduce((a, b) => sampleData.brain_condition_counts[a] > sampleData.brain_condition_counts[b] ? a : b);
    document.getElementById('main-condition').textContent = mainCond;

    // === 通用配色 ===
    const chartColors = [
        'rgba(52, 152, 219, 0.7)',
        'rgba(46, 204, 113, 0.7)',
        'rgba(155, 89, 182, 0.7)',
        'rgba(52, 73, 94, 0.7)',
        'rgba(231, 76, 60, 0.7)',
        'rgba(241, 196, 15, 0.7)',
        'rgba(230, 126, 34, 0.7)',
        'rgba(149, 165, 166, 0.7)'
    ];

    // === 创建图表函数 ===
    function createChart(id, type, labels, data, datasetLabel = '') {
        const ctx = document.getElementById(id).getContext('2d');
        const bgColors = (type === 'bar')
            ? chartColors[0]
            : labels.map((_, i) => chartColors[i % chartColors.length]);

        new Chart(ctx, {
            type: type,
            data: {
                labels: labels,
                datasets: [{
                    label: datasetLabel,
                    data: data,
                    backgroundColor: bgColors,
                    borderColor: 'rgba(255, 255, 255, 0.8)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: (type === 'bar' ? 'top' : 'right'),
                        labels: { font: { size: 12 } }
                    }
                }
            }
        });
    }

    // === 渲染所有图表 ===
    document.addEventListener('DOMContentLoaded', () => {
        createChart('genderChart', 'pie',
            Object.keys(sampleData.gender_distribution),
            Object.values(sampleData.gender_distribution)
        );
        createChart('ageChart', 'bar',
            Object.keys(sampleData.age_groups),
            Object.values(sampleData.age_groups),
            '患者人数'
        );
        createChart('statusChart', 'pie',
            Object.keys(sampleData.status_counts),
            Object.values(sampleData.status_counts)
        );
        createChart('bloodTypeChart', 'pie',
            Object.keys(sampleData.blood_types),
            Object.values(sampleData.blood_types)
        );
        createChart('ctTypeChart', 'pie',
            Object.keys(sampleData.ct_types),
            Object.values(sampleData.ct_types)
        );
        createChart('cognitiveScoreChart', 'pie',
            Object.keys(sampleData.cognitive_scores),
            Object.values(sampleData.cognitive_scores)
        );
        createChart('brainConditionChart', 'bar',
            Object.keys(sampleData.brain_condition_counts),
            Object.values(sampleData.brain_condition_counts),
            '患者人数'
        );
        createChart('medicationChart', 'bar',
            Object.keys(sampleData.medications),
            Object.values(sampleData.medications),
            '患者人数'
        );
        createChart('anxietyChart', 'bar',
            Object.keys(sampleData.anxiety_levels),
            Object.values(sampleData.anxiety_levels),
            '患者人数'
        );
        createChart('depressionChart', 'bar',
            Object.keys(sampleData.depression_levels),
            Object.values(sampleData.depression_levels),
            '患者人数'
        );
    });
