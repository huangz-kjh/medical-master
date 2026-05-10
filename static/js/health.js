// 示例数据 - 用于跟踪的月份标签
var timeLabels = ['2024-05', '2024-06', '2024-07', '2024-08', '2024-09', '2024-10', '2024-11', '2024-12', '2025-01', '2025-02', '2025-03', '2025-04'];

$(function(){
    initCharts();
    $(window).on('resize', function() {
        cognitiveRadarChart.resize();
        cognitiveLineChart.resize();
        biomarkersChart.resize();
        cognitiveBarChart.resize();
        cognitiveTrendChart.resize();
        ageRiskChart.resize();
    });
});

function initCharts(){
    // 认知健康评估雷达图
    var cognitiveRadarChart = echarts.init(document.getElementById('cognitiveRadarChart'));
    cognitiveRadarChart.setOption({
        color: ['#4fc3f7'],
        tooltip: {
            trigger: 'item'
        },
        radar: {
            indicator: [
                { name: '记忆', max: 100 },
                { name: '注意力', max: 100 },
                { name: '执行功能', max: 100 },
                { name: '语言能力', max: 100 },
                { name: '空间感知', max: 100 }
            ],
            radius: '65%',
            splitArea: {
                areaStyle: {
                    color: ['rgba(19, 55, 82, 0.3)', 'rgba(19, 55, 82, 0.5)'],
                    shadowBlur: 10
                }
            },
            axisLine: {
                lineStyle: {
                    color: 'rgba(79, 195, 247, 0.3)'
                }
            },
            splitLine: {
                lineStyle: {
                    color: 'rgba(79, 195, 247, 0.3)'
                }
            },
            name: {
                textStyle: {
                    color: '#fff'
                }
            }
        },
        series: [{
            name: '认知功能',
            type: 'radar',
            data: [
                {
                    value: [85, 92, 78, 88, 67],
                    name: '当前评估',
                    symbol: 'circle',
                    symbolSize: 8,
                    lineStyle: {
                        width: 2
                    },
                    areaStyle: {
                        opacity: 0.3
                    }
                }
            ]
        }]
    });

    // 认知健康趋势折线图
    var cognitiveLineChart = echarts.init(document.getElementById('cognitiveLineChart'));
    cognitiveLineChart.setOption({
        title: {
            text: '认知趋势',
            textStyle: {
                fontSize: 16,
                color: '#4fc3f7'
            }
        },
        color: ["#4fc3f7"],
        grid: {
            left: '15%',
            right: '5%',
            bottom: '15%'
        },
        tooltip: {
            trigger: 'axis',
            formatter: function(params) {
                return params[0].name + '<br/>' + params[0].seriesName + ': ' + params[0].value;
            }
        },
        yAxis: {
            type: 'value',
            min: 60,
            max: 100,
            axisLine: {
                lineStyle: {
                    color: '#4fc3f7'
                }
            },
            splitLine: {
                lineStyle: {
                    color: 'rgba(79, 195, 247, 0.1)'
                }
            },
            axisLabel: {
                textStyle: {
                    color: '#fff'
                }
            }
        },
        xAxis: {
            type: 'category',
            data: timeLabels,
            boundaryGap: false,
            axisLine: {
                lineStyle: {
                    color: '#4fc3f7'
                }
            },
            axisLabel: {
                textStyle: {
                    color: '#fff'
                },
                rotate: 45
            }
        },
        series: [{
            name: '认知得分',
            type: 'line',
            smooth: true,
            symbol: 'circle',
            symbolSize: 7,
            itemStyle: {
                normal: {
                    areaStyle: {
                        type: 'default',
                        opacity: 0.3
                    }
                }
            },
            data: [90, 89, 88, 87, 86, 85, 84, 83, 82, 83, 82, 82]
        }]
    });

    // 关键生物标志物图表
    var biomarkersChart = echarts.init(document.getElementById('biomarkersChart'));
    biomarkersChart.setOption({
        color: ['#f44336'],
        grid: {
            left: '5%',
            right: '5%',
            bottom: '10%',
            containLabel: true
        },
        tooltip: {
            trigger: 'axis',
            axisPointer: {
                type: 'shadow'
            }
        },
        yAxis: {
            type: 'category',
            data: ['淀粉样蛋白-β', 'Tau蛋白', 'C反应蛋白', '同型半胱氨酸', '脑源性神经营养因子', '胰岛素抵抗', '皮质醇'],
            axisLine: {
                lineStyle: {
                    color: '#f44336'
                }
            },
            axisLabel: {
                textStyle: {
                    color: '#fff'
                }
            }
        },
        xAxis: {
            type: 'value',
            axisLine: {
                lineStyle: {
                    color: '#f44336'
                }
            },
            splitLine: {
                lineStyle: {
                    color: 'rgba(244, 67, 54, 0.1)'
                }
            },
            axisLabel: {
                textStyle: {
                    color: '#fff'
                },
                formatter: function(value) {
                    return value + '%';
                }
            }
        },
        series: [{
            name: '偏离正常值',
            type: 'bar',
            barWidth: 20,
            data: [48, 32, 25, 22, 18, 15, 12],
            itemStyle: {
                normal: {
                    barBorderRadius: [0, 10, 10, 0],
                    color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                        {offset: 0, color: '#f44336'},
                        {offset: 1, color: '#ff9800'}
                    ])
                }
            },
            label: {
                show: true,
                position: 'right',
                formatter: '{c}%',
                textStyle: {
                    color: '#fff'
                }
            }
        }]
    });

    // 认知功能跟踪条形图
    var cognitiveBarChart = echarts.init(document.getElementById('cognitiveBarChart'));

    // 定义渐变色
    var colors = ['#3f51b5', '#009688', '#9c27b0', '#ff9800', '#e91e63', '#2196f3', '#4caf50', '#ffeb3b'];

    cognitiveBarChart.setOption({
        grid: {
            top: '12%',
            left: '30%'
        },
        tooltip: {
            trigger: 'axis',
            axisPointer: {
                type: 'shadow'
            }
        },
        xAxis: {
            show: false
        },
        yAxis: [{
            show: true,
            data: ['记忆回忆', '问题解决', '语言流畅性', '模式识别', '处理速度', '注意力持续', '心理灵活性', '学习能力'],
            inverse: true,
            axisLine: {
                show: false
            },
            splitLine: {
                show: false
            },
            axisTick: {
                show: false
            },
            axisLabel: {
                color: '#fff',
                formatter: (value, index) => {
                    return [
                        `{lg|${index+1}}  ` + '{title|' + value + '} '
                    ].join('\n')
                },
                rich: {
                    lg: {
                        backgroundColor: '#009688',
                        color: '#fff',
                        borderRadius: 15,
                        align: 'center',
                        width: 15,
                        height: 15
                    },
                }
            },
        }, {
            show: true,
            inverse: true,
            data: [90, 85, 82, 78, 75, 73, 70, 68],
            axisLabel: {
                textStyle: {
                    fontSize: 12,
                    color: '#fff',
                },
            },
            axisLine: {
                show: false
            },
            splitLine: {
                show: false
            },
            axisTick: {
                show: false
            },
        }],
        series: [{
            name: '得分',
            type: 'bar',
            yAxisIndex: 0,
            data: [90, 85, 82, 78, 75, 73, 70, 68],
            barWidth: 10,
            itemStyle: {
                normal: {
                    barBorderRadius: 20,
                    color: function(params) {
                        return colors[params.dataIndex % colors.length];
                    },
                }
            },
            label: {
                normal: {
                    show: true,
                    position: 'inside',
                    formatter: '{c}'
                }
            },
        }, {
            name: '条形框架',
            type: 'bar',
            yAxisIndex: 1,
            barGap: '-100%',
            data: [100, 100, 100, 100, 100, 100, 100, 100],
            barWidth: 15,
            itemStyle: {
                normal: {
                    color: 'none',
                    borderColor: '#00c1de',
                    borderWidth: 1,
                    barBorderRadius: 15,
                }
            }
        }]
    });

    // 认知功能趋势图
    var cognitiveTrendChart = echarts.init(document.getElementById('cognitiveTrendChart'));
    cognitiveTrendChart.setOption({
        title: {
            text: '纵向评估',
            textStyle: {
                fontSize: 16,
                color: '#4db6ac'
            },
            x: "center"
        },
        color: ["#4db6ac", "#ef5350", "#7986cb"],
        grid: {
            left: '15%',
            right: '5%',
            bottom: '25%'
        },
        tooltip: {
            trigger: 'axis'
        },
        legend: {
            data: ['记忆', '执行功能', '处理速度'],
            textStyle: {
                color: '#fff'
            },
            top: 30
        },
        yAxis: {
            type: 'value',
            min: 60,
            max: 100,
            axisLine: {
                lineStyle: {
                    color: '#4db6ac'
                }
            },
            splitLine: {
                lineStyle: {
                    color: 'rgba(77, 182, 172, 0.1)'
                }
            },
            axisLabel: {
                textStyle: {
                    color: '#fff'
                }
            }
        },
        xAxis: {
            type: 'category',
            data: timeLabels,
            boundaryGap: false,
            axisLine: {
                lineStyle: {
                    color: '#4db6ac'
                }
            },
            axisLabel: {
                textStyle: {
                    color: '#fff'
                },
                rotate: 45
            }
        },
        series: [
            {
                name: '记忆',
                type: 'line',
                smooth: true,
                symbol: 'circle',
                symbolSize: 5,
                data: [92, 91, 90, 89, 88, 87, 86, 85, 83, 84, 83, 85]
            },
            {
                name: '执行功能',
                type: 'line',
                smooth: true,
                symbol: 'circle',
                symbolSize: 5,
                data: [88, 87, 86, 85, 84, 82, 81, 80, 78, 77, 76, 78]
            },
            {
                name: '处理速度',
                type: 'line',
                smooth: true,
                symbol: 'circle',
                symbolSize: 5,
                data: [90, 89, 87, 86, 85, 83, 81, 80, 79, 77, 75, 75]
            }
        ]
    });

    // 年龄相关风险因素饼图
    var ageRiskChart = echarts.init(document.getElementById('ageRiskChart'));
    ageRiskChart.setOption({
        color: ["#8bc34a", "#ff9800", "#f44336", "#9c27b0", "#3f51b5", "#00bcd4"],
        tooltip: {
            trigger: 'item',
            formatter: "{b}: {c}% ({d}%)"
        },
        legend: {
            orient: 'vertical',
            left: 'left',
            textStyle: {
                color: '#fff'
            },
            data: ['阿尔茨海默病', '心血管风险', '代谢综合征', '抑郁症', '骨关节炎', '泌尿系统问题']
        },
        series: [
            {
                name: '风险概况',
                type: 'pie',
                radius: ['45%', '70%'],
                center: ['60%', '55%'],
                roseType: 'radius',
                label: {
                    show: false
                },
                emphasis: {
                    label: {
                        show: true
                    }
                },
                data: [
                    {value: 35, name: '阿尔茨海默病'},
                    {value: 25, name: '心血管风险'},
                    {value: 15, name: '代谢综合征'},
                    {value: 12, name: '抑郁症'},
                    {value: 8, name: '骨关节炎'},
                    {value: 5, name: '泌尿系统问题'}
                ]
            }
        ]
    });
}
