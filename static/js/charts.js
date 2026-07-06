// Smart Lender Chart.js Visualization Logic

document.addEventListener('DOMContentLoaded', function () {
    // 1. User Dashboard: Individual Prediction Ratio Doughnut Chart
    const userChartCanvas = document.getElementById('userPredictionsChart');
    if (userChartCanvas) {
        const eligibleCount = parseInt(userChartCanvas.dataset.eligible || '0');
        const totalCount = parseInt(userChartCanvas.dataset.total || '0');
        const ineligibleCount = totalCount - eligibleCount;
        
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        const labelColor = isDark ? '#94A3B8' : '#64748B';
        
        new Chart(userChartCanvas, {
            type: 'doughnut',
            data: {
                labels: ['Approved Eligibility', 'Ineligible Standards'],
                datasets: [{
                    data: [eligibleCount, ineligibleCount],
                    backgroundColor: ['#10B981', '#F43F5E'],
                    borderColor: isDark ? '#0F172A' : '#FFFFFF',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: labelColor,
                            font: { family: 'Outfit', size: 12 }
                        }
                    }
                },
                cutout: '70%'
            }
        });
    }

    // 2. Admin Dashboard: Global Prediction Metrics Pie Chart
    const adminPieCanvas = document.getElementById('adminPredictionsDistribution');
    if (adminPieCanvas) {
        const eligibleCount = parseInt(adminPieCanvas.dataset.eligible || '0');
        const totalCount = parseInt(adminPieCanvas.dataset.total || '0');
        const ineligibleCount = totalCount - eligibleCount;
        
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        const labelColor = isDark ? '#94A3B8' : '#64748B';
        
        new Chart(adminPieCanvas, {
            type: 'pie',
            data: {
                labels: ['Eligible Applications', 'Ineligible Applications'],
                datasets: [{
                    data: [eligibleCount, ineligibleCount],
                    backgroundColor: ['#10B981', '#F43F5E'],
                    borderColor: isDark ? '#0F172A' : '#FFFFFF',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: labelColor,
                            font: { family: 'Outfit', size: 12 }
                        }
                    }
                }
            }
        });
    }

    // 3. Admin & User Dashboards: Model Accuracies Horizontal Bar Chart
    const modelAccuracyCanvas = document.getElementById('modelAccuracyChart');
    if (modelAccuracyCanvas) {
        try {
            const rawData = modelAccuracyCanvas.dataset.comparison || '[]';
            const comparisonData = JSON.parse(rawData);
            
            // Sort models by accuracy ascending for horiz bar chart
            comparisonData.sort((a, b) => a['CV Accuracy'] - b['CV Accuracy']);
            
            const labels = comparisonData.map(item => item.Model);
            const accuracies = comparisonData.map(item => item['CV Accuracy'] * 100); // convert to %
            
            const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
            const labelColor = isDark ? '#94A3B8' : '#64748B';
            const gridColor = isDark ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.08)';
            
            new Chart(modelAccuracyCanvas, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Cross Validation Accuracy (%)',
                        data: accuracies,
                        backgroundColor: '#4F46E5',
                        borderRadius: 5,
                        borderWidth: 0
                    }]
                },
                options: {
                    indexAxis: 'y',
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    return `Accuracy: ${context.raw.toFixed(2)}%`;
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            min: 50,
                            max: 100,
                            ticks: {
                                color: labelColor,
                                font: { family: 'Outfit' }
                            },
                            grid: {
                                color: gridColor
                            }
                        },
                        y: {
                            ticks: {
                                color: labelColor,
                                font: { family: 'Outfit' }
                            },
                            grid: {
                                display: false
                            }
                        }
                    }
                }
            });
        } catch (e) {
            console.error("Error parsing model comparison dataset:", e);
        }
    }
});
