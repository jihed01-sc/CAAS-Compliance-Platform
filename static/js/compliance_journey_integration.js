// ===== ENHANCED NGROK DEPLOYMENT AND COMPLIANCE JOURNEY INTEGRATION =====

// Enhanced Extract results from ngrok deployment with journey step updates
function extractDeploymentResults(systemId, deploymentId, systemName) {
    if (!deploymentId) {
        alert('No deployment ID found. Please deploy the system first.');
        return;
    }

    if (!confirm(`Extract results for "${systemName}" from ngrok deployment?`)) {
        return;
    }

    // Show loading indicator
    const extractBtn = document.querySelector(`[onclick*="extractDeploymentResults(${systemId}"]`);
    if (extractBtn) {
        extractBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Extracting...';
        extractBtn.disabled = true;
    }

    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
                    document.querySelector('meta[name=csrf-token]')?.getAttribute('content');

    fetch('/extract-results/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrfToken,
            'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: `system_id=${systemId}&deployment_id=${deploymentId}`
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Display results summary
            const summary = data.summary;
            const resultsHtml = `
                📊 DEPLOYMENT RESULTS EXTRACTED

                System: ${systemName}
                Deployment ID: ${deploymentId}

                📈 SUMMARY:
                • Total Controls: ${summary.total_controls}
                • Matched Controls: ${summary.matched_controls}
                • Improved Controls: ${summary.improved_controls}
                • Needs Attention: ${summary.needs_attention}

                🎯 NEXT STEPS:
                • Review detailed results in the table below
                • Check control recommendations
                • Update control statuses as needed
            `;

            alert(resultsHtml);

            // Update journey steps based on extraction results
            updateJourneyStepsFromExtraction(data);

            // Show detailed results modal
            showDetailedResults(data.results, systemName);

            if (extractBtn) {
                extractBtn.innerHTML = '<i class="fas fa-download"></i> Results Extracted';
                extractBtn.classList.add('extracted');
                extractBtn.disabled = false;
            }

            // Update compliance progress
            updateComplianceProgress(data.complianceScore, data.improvementPercentage);

        } else {
            alert(`❌ Result Extraction Failed: ${data.message}`);
            if (extractBtn) {
                extractBtn.innerHTML = '<i class="fas fa-download"></i> Extract Results';
                extractBtn.disabled = false;
            }
        }
    })
    .catch(error => {
        console.error('Extraction error:', error);
        alert(`❌ Extraction Error: ${error.message}`);
        if (extractBtn) {
            extractBtn.innerHTML = '<i class="fas fa-download"></i> Extract Results';
            extractBtn.disabled = false;
        }
    });
}

// Update journey steps based on extraction results
function updateJourneyStepsFromExtraction(extractionData) {
    const journeySteps = document.querySelectorAll('.journey-step');

    // Update Gap Analysis step - mark as completed after extraction
    const gapAnalysisStep = journeySteps[1]; // Second step
    if (gapAnalysisStep) {
        updateJourneyStepStatus(gapAnalysisStep, 'completed', 100);
        addStepBadge(gapAnalysisStep, '📊 Results Extracted', 'var(--neon-purple)');
    }

    // Update Recommendations step - mark as in progress
    const recommendationsStep = journeySteps[2]; // Third step
    if (recommendationsStep) {
        updateJourneyStepStatus(recommendationsStep, 'in_progress', 75);
        addStepBadge(recommendationsStep, '🔄 Generating', 'var(--warning)');
    }

    // Show notification
    showProgressNotification(`📈 Gap Analysis completed! ${extractionData.summary.matched_controls} controls analyzed.`);
}

// Update journey step status with visual effects
function updateJourneyStepStatus(stepElement, status, progress) {
    const statusClasses = {
        'completed': 'var(--success)',
        'in_progress': 'var(--warning)',
        'pending': 'var(--border-color)'
    };

    // Update border color
    stepElement.style.borderColor = statusClasses[status];

    // Update progress bar
    const progressBar = stepElement.querySelector('.progress-bar');
    if (progressBar) {
        progressBar.style.width = progress + '%';
        progressBar.style.background = statusClasses[status];
    }

    // Update status text
    const statusSpan = stepElement.querySelector('.step-status');
    if (statusSpan) {
        if (status === 'completed') {
            statusSpan.textContent = '✓ Completed';
            statusSpan.style.color = 'var(--success)';
        } else if (status === 'in_progress') {
            statusSpan.textContent = '⟳ In Progress';
            statusSpan.style.color = 'var(--warning)';
        }
    }

    // Add animation
    stepElement.style.transform = 'scale(1.05)';
    setTimeout(() => {
        stepElement.style.transform = 'scale(1)';
    }, 300);
}

// Add status badge to journey step
function addStepBadge(stepElement, text, color) {
    // Remove existing badge
    const existingBadge = stepElement.querySelector('.step-badge');
    if (existingBadge) {
        existingBadge.remove();
    }

    // Create new badge
    const badge = document.createElement('div');
    badge.className = 'step-badge';
    badge.textContent = text;
    badge.style.cssText = `
        position: absolute;
        top: -10px;
        right: -10px;
        background: ${color};
        color: white;
        padding: 0.2rem 0.5rem;
        border-radius: 12px;
        font-size: 0.7rem;
        font-weight: 600;
        z-index: 10;
        animation: badgePulse 1s ease-in-out;
    `;

    stepElement.style.position = 'relative';
    stepElement.appendChild(badge);
}

// ===== QUESTIONNAIRE RESULTS INTEGRATION =====

// Process questionnaire results and update compliance progress
function processQuestionnaireResults(questionnaireData) {
    const {
        totalQuestions,
        correctAnswers,
        complianceScore,
        previousScore,
        recommendations
    } = questionnaireData;

    const improvement = complianceScore - previousScore;

    // Update compliance progress section
    updateComplianceProgress(complianceScore, improvement);

    // Update journey steps
    updateJourneyStepsFromQuestionnaire(complianceScore, improvement);

    // Show detailed results
    showQuestionnaireResults(questionnaireData);
}

// Update compliance progress with new scores
function updateComplianceProgress(newScore, improvement) {
    // Update completion percentage
    const completionElement = document.querySelector('.progress-bar-container .progress-bar');
    if (completionElement) {
        completionElement.style.width = newScore + '%';

        // Add glow effect for improvement
        if (improvement > 0) {
            completionElement.style.boxShadow = '0 0 20px var(--success)';
            setTimeout(() => {
                completionElement.style.boxShadow = '';
            }, 3000);
        }
    }

    // Update score circle
    const scoreCircle = document.querySelector('.score-circle span');
    if (scoreCircle) {
        const currentScore = parseInt(scoreCircle.textContent);
        animateScoreChange(scoreCircle, currentScore, newScore);
    }

    // Show improvement notification
    if (improvement > 0) {
        showProgressNotification(`🎉 Compliance Score Improved by ${improvement.toFixed(1)}%! New Score: ${newScore.toFixed(1)}%`);
    }
}

// Animate score change with counting effect
function animateScoreChange(element, fromScore, toScore) {
    const duration = 2000; // 2 seconds
    const steps = 60;
    const stepDuration = duration / steps;
    const scoreIncrement = (toScore - fromScore) / steps;

    let currentStep = 0;

    const interval = setInterval(() => {
        currentStep++;
        const currentScore = fromScore + (scoreIncrement * currentStep);
        element.textContent = Math.round(currentScore);

        // Add glow effect during animation
        element.style.textShadow = '0 0 15px var(--neon-green)';

        if (currentStep >= steps) {
            clearInterval(interval);
            element.textContent = Math.round(toScore);
            element.style.textShadow = '';
        }
    }, stepDuration);
}

// Update journey steps based on questionnaire results
function updateJourneyStepsFromQuestionnaire(score, improvement) {
    const journeySteps = document.querySelectorAll('.journey-step');

    // Update Re-evaluation step
    const reEvaluationStep = journeySteps[3]; // Fourth step
    if (reEvaluationStep && score >= 70) {
        updateJourneyStepStatus(reEvaluationStep, 'completed', 100);
        addStepBadge(reEvaluationStep, '✅ Passed', 'var(--success)');
    } else if (reEvaluationStep) {
        updateJourneyStepStatus(reEvaluationStep, 'in_progress', Math.min(score, 90));
        addStepBadge(reEvaluationStep, '📝 Assessed', 'var(--neon-blue)');
    }

    // Update Report Generation step if score is high enough
    const reportStep = journeySteps[4]; // Fifth step
    if (reportStep && score >= 80) {
        updateJourneyStepStatus(reportStep, 'in_progress', 50);
        addStepBadge(reportStep, '📄 Ready', 'var(--neon-purple)');
    }
}

// Show questionnaire results modal
function showQuestionnaireResults(data) {
    const modalHtml = `
        <div id="questionnaireResultsModal" class="modal-overlay" onclick="closeQuestionnaireResults()">
            <div class="modal-content" onclick="event.stopPropagation()">
                <div class="modal-header">
                    <h3><i class="fas fa-chart-bar"></i> Questionnaire Results</h3>
                    <button class="modal-close" onclick="closeQuestionnaireResults()">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="results-summary">
                        <h4>📊 Assessment Summary</h4>
                        <div class="score-display">
                            <div class="score-circle-large">
                                <span class="score-number">${data.complianceScore.toFixed(1)}%</span>
                                <span class="score-label">Compliance Score</span>
                            </div>
                            <div class="score-details">
                                <p><strong>Questions Answered:</strong> ${data.totalQuestions}</p>
                                <p><strong>Correct Answers:</strong> ${data.correctAnswers}</p>
                                <p><strong>Improvement:</strong> <span class="score-improvement">+${(data.complianceScore - data.previousScore).toFixed(1)}%</span></p>
                            </div>
                        </div>
                    </div>

                    <div class="recommendations-section">
                        <h4>🎯 Recommendations</h4>
                        <ul class="recommendations-list">
                            ${data.recommendations.map(rec => `<li>${rec}</li>`).join('')}
                        </ul>
                    </div>

                    <div class="next-steps">
                        <h4>🚀 Next Steps</h4>
                        <div class="steps-grid">
                            <div class="next-step-card" onclick="navigateToControls()">
                                <i class="fas fa-clipboard-check"></i>
                                <h5>Review Controls</h5>
                                <p>Check updated control statuses</p>
                            </div>
                            <div class="next-step-card" onclick="navigateToReports()">
                                <i class="fas fa-file-alt"></i>
                                <h5>Generate Report</h5>
                                <p>Create compliance documentation</p>
                            </div>
                            <div class="next-step-card" onclick="navigateToNextStep()">
                                <i class="fas fa-sync-alt"></i>
                                <h5>Continue Journey</h5>
                                <p>Proceed to next phase</p>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-primary" onclick="closeQuestionnaireResults()">Continue</button>
                    <button class="btn btn-success" onclick="navigateToNextStep()">Next Step</button>
                </div>
            </div>
        </div>
    `;

    // Add modal to body
    document.body.insertAdjacentHTML('beforeend', modalHtml);

    // Add enhanced modal styles
    addQuestionnaireModalStyles();
}

// Close questionnaire results modal
function closeQuestionnaireResults() {
    const modal = document.getElementById('questionnaireResultsModal');
    if (modal) {
        modal.remove();
    }
}

// Navigate to next step in journey
function navigateToNextStep() {
    closeQuestionnaireResults();
    // Determine next step based on current progress
    const currentScore = parseFloat(document.querySelector('.score-circle span').textContent);

    if (currentScore >= 80) {
        window.location.href = '/compliance/reports/';
    } else if (currentScore >= 70) {
        window.location.href = '/compliance/re-evaluation/';
    } else {
        window.location.href = '/compliance/recommendations/';
    }
}

// Navigate to specific sections
function navigateToControls() {
    closeQuestionnaireResults();
    window.location.href = '/compliance/controls/';
}

function navigateToReports() {
    closeQuestionnaireResults();
    window.location.href = '/compliance/reports/';
}

// Show progress notification
function showProgressNotification(message) {
    const notification = document.createElement('div');
    notification.className = 'progress-update-notification';
    notification.innerHTML = `
        <div style="display: flex; align-items: center; gap: 0.5rem;">
            <i class="fas fa-check-circle" style="color: var(--success);"></i>
            <span>${message}</span>
        </div>
    `;

    document.body.appendChild(notification);

    // Auto remove after 5 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOutRight 0.5s ease-in';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 500);
    }, 5000);
}

// Add enhanced styles for questionnaire results
function addQuestionnaireModalStyles() {
    if (!document.getElementById('questionnaireModalStyles')) {
        const styles = document.createElement('style');
        styles.id = 'questionnaireModalStyles';
        styles.textContent = `
            .modal-overlay {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.8);
                display: flex;
                justify-content: center;
                align-items: center;
                z-index: 10000;
            }

            .modal-content {
                background: var(--card-bg);
                border-radius: 12px;
                max-width: 90vw;
                max-height: 90vh;
                overflow-y: auto;
                border: 1px solid var(--border-color);
            }

            .modal-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 1.5rem;
                border-bottom: 1px solid var(--border-color);
            }

            .modal-header h3 {
                color: var(--neon-blue);
                margin: 0;
            }

            .modal-close {
                background: none;
                border: none;
                font-size: 1.5rem;
                color: var(--text-secondary);
                cursor: pointer;
            }

            .modal-body {
                padding: 1.5rem;
            }

            .score-display {
                display: flex;
                align-items: center;
                gap: 2rem;
                margin: 1rem 0;
            }

            .score-circle-large {
                width: 120px;
                height: 120px;
                border-radius: 50%;
                border: 4px solid var(--success);
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                background: radial-gradient(circle, var(--success)10, transparent 50%);
            }

            .score-number {
                font-size: 2rem;
                font-weight: bold;
                color: var(--success);
            }

            .score-label {
                font-size: 0.8rem;
                color: var(--text-secondary);
            }

            .score-details p {
                margin: 0.5rem 0;
                color: var(--text-primary);
            }

            .score-improvement {
                color: var(--success);
                font-weight: bold;
                animation: scoreGlow 1s ease-in-out;
            }

            @keyframes scoreGlow {
                0%, 100% {
                    text-shadow: 0 0 5px var(--success);
                }
                50% {
                    text-shadow: 0 0 15px var(--success), 0 0 25px var(--success);
                }
            }

            .recommendations-list {
                list-style: none;
                padding: 0;
            }

            .recommendations-list li {
                padding: 0.5rem;
                margin: 0.5rem 0;
                background: var(--secondary-bg);
                border-radius: 8px;
                border-left: 4px solid var(--neon-blue);
            }

            .steps-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                gap: 1rem;
                margin-top: 1rem;
            }

            .next-step-card {
                background: var(--secondary-bg);
                padding: 1rem;
                border-radius: 8px;
                text-align: center;
                transition: all 0.3s ease;
                cursor: pointer;
                border: 1px solid var(--border-color);
            }

            .next-step-card:hover {
                transform: translateY(-2px);
                border-color: var(--neon-blue);
                box-shadow: 0 4px 15px rgba(0, 212, 255, 0.3);
            }

            .next-step-card i {
                font-size: 2rem;
                color: var(--neon-blue);
                margin-bottom: 0.5rem;
            }

            .next-step-card h5 {
                margin: 0.5rem 0;
                color: var(--text-primary);
            }

            .next-step-card p {
                margin: 0;
                font-size: 0.8rem;
                color: var(--text-secondary);
            }

            .modal-footer {
                display: flex;
                gap: 1rem;
                padding: 1.5rem;
                border-top: 1px solid var(--border-color);
                justify-content: flex-end;
            }

            .btn {
                padding: 0.8rem 1.5rem;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                font-weight: 600;
                transition: all 0.3s ease;
            }

            .btn-primary {
                background: var(--neon-blue);
                color: white;
            }

            .btn-success {
                background: var(--success);
                color: white;
            }

            .btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
            }

            .progress-update-notification {
                position: fixed;
                top: 20px;
                right: 20px;
                background: var(--card-bg);
                border: 2px solid var(--success);
                border-radius: 12px;
                padding: 1rem;
                z-index: 1000;
                max-width: 300px;
                animation: slideInRight 0.5s ease-out;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
            }

            @keyframes slideInRight {
                from {
                    transform: translateX(100%);
                    opacity: 0;
                }
                to {
                    transform: translateX(0);
                    opacity: 1;
                }
            }

            @keyframes slideOutRight {
                from {
                    transform: translateX(0);
                    opacity: 1;
                }
                to {
                    transform: translateX(100%);
                    opacity: 0;
                }
            }

            @keyframes badgePulse {
                0%, 100% {
                    transform: scale(1);
                }
                50% {
                    transform: scale(1.1);
                }
            }

            .step-badge {
                animation: badgePulse 1s ease-in-out;
            }
        `;
        document.head.appendChild(styles);
    }
}

// Enhanced deployment check with journey updates
function checkDeploymentStatus() {
    // Check each system's deployment status
    const systemRows = document.querySelectorAll('tr[data-system-id]');
    systemRows.forEach(row => {
        const systemId = row.dataset.systemId;
        if (systemId) {
            fetch(`/check-deployment-status/${systemId}/`)
                .then(response => response.json())
                .then(data => {
                    if (data.success && data.deployed) {
                        const deployBtn = row.querySelector('.deploy-btn');
                        if (deployBtn) {
                            deployBtn.innerHTML = '<i class="fas fa-cloud-upload-alt"></i> Deployed';
                            deployBtn.classList.add('deployed');
                        }

                        // Show extract results button if deployed
                        const deploymentId = data.deployment_info.deployment_id;
                        const systemName = row.querySelector('.system-name')?.textContent || 'System';
                        showExtractResultsButton(systemId, deploymentId, systemName);

                        // Update diagnostic step if deployment exists
                        updateDiagnosticStepFromDeployment();
                    }
                })
                .catch(error => console.log('Deployment status check failed:', error));
        }
    });
}

// Update diagnostic step when deployment is detected
function updateDiagnosticStepFromDeployment() {
    const journeySteps = document.querySelectorAll('.journey-step');
    const diagnosticStep = journeySteps[0]; // First step

    if (diagnosticStep) {
        updateJourneyStepStatus(diagnosticStep, 'completed', 100);
        addStepBadge(diagnosticStep, '🚀 Deployed', 'var(--neon-blue)');
    }
}

// Check questionnaire completion status
function checkQuestionnaireCompletion() {
    fetch('/compliance/api/questionnaire-status/')
        .then(response => response.json())
        .then(data => {
            if (data.completed) {
                // Show Extract Results buttons for completed systems
                data.completed_systems.forEach(system => {
                    showExtractResultsAfterQuestionnaire(system.system_id, system.system_name);
                });

                // Update journey progress if results are available
                if (data.latest_score > 0) {
                    updateJourneyProgressFromQuestionnaire(data.results);
                }

                // Show notification about questionnaire completion
                showProgressNotification(`✅ Questionnaire completed! Extract Results buttons are now available.`);
            }
        })
        .catch(error => console.log('Questionnaire status check failed:', error));
}

// Show Extract Results button after questionnaire completion
function showExtractResultsAfterQuestionnaire(systemId, systemName) {
    const systemRow = document.querySelector(`tr[data-system-id="${systemId}"]`);
    if (systemRow) {
        const actionsCell = systemRow.querySelector('td:last-child');

        // Check if Extract Results button already exists
        if (!actionsCell.querySelector('.extract-results-btn')) {
            // Create deployment info display
            const deploymentInfo = document.createElement('div');
            deploymentInfo.className = 'deployment-info';
            deploymentInfo.innerHTML = `
                <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
                    <i class="fas fa-check-circle" style="color: var(--success);"></i>
                    <span style="color: var(--success); font-size: 0.8rem;">Questionnaire Completed</span>
                </div>
            `;

            // Create Extract Results button
            const extractBtn = document.createElement('button');
            extractBtn.className = 'table-button success extract-results-btn';
            extractBtn.innerHTML = '<i class="fas fa-download"></i> Extract Results';
            extractBtn.onclick = () => extractResultsFromQuestionnaire(systemId, systemName);

            // Add both elements to actions cell
            actionsCell.appendChild(deploymentInfo);
            actionsCell.appendChild(extractBtn);

            // Add visual highlight
            systemRow.style.background = 'linear-gradient(135deg, var(--secondary-bg), rgba(0, 255, 136, 0.05))';
            systemRow.style.border = '1px solid rgba(0, 255, 136, 0.3)';
        }
    }
}

// Extract results specifically from questionnaire completion
function extractResultsFromQuestionnaire(systemId, systemName) {
    if (!confirm(`Extract questionnaire results for "${systemName}"?`)) {
        return;
    }

    // Show loading indicator
    const extractBtn = document.querySelector(`tr[data-system-id="${systemId}"] .extract-results-btn`);
    if (extractBtn) {
        extractBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Extracting...';
        extractBtn.disabled = true;
    }

    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
                    document.querySelector('meta[name=csrf-token]')?.getAttribute('content');

    // Use a placeholder deployment ID for questionnaire-based extraction
    const deploymentId = `questionnaire_${systemId}_${Date.now()}`;

    fetch('/compliance/extract-results/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrfToken,
            'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: `system_id=${systemId}&deployment_id=${deploymentId}`
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Display enhanced results summary for questionnaire
            const summary = data.summary;
            const resultsHtml = `
                🎯 QUESTIONNAIRE RESULTS EXTRACTED

                System: ${systemName}
                Questionnaire Completed: ${data.questionnaireCompleted ? 'Yes' : 'No'}

                📈 ANALYSIS SUMMARY:
                • Total Controls Analyzed: ${summary.total_controls}
                • Compliant Controls: ${summary.matched_controls}
                • Improved Controls: ${summary.improved_controls}
                • Controls Needing Attention: ${summary.needs_attention}
                • Overall Compliance Score: ${data.complianceScore.toFixed(1)}%

                🎉 ACHIEVEMENTS:
                ${data.questionnaireCompleted ? '• Questionnaire successfully completed' : ''}
                ${data.improvementPercentage > 0 ? `• ${data.improvementPercentage} controls improved` : ''}
                ${data.complianceScore >= 80 ? '• Excellent compliance level achieved!' : 
                  data.complianceScore >= 60 ? '• Good compliance progress made' : 
                  '• Foundation established for improvement'}

                🚀 NEXT STEPS:
                • Check updated journey progress below
                • Review individual control statuses
                • Proceed to next compliance phase
            `;

            alert(resultsHtml);

            // Update journey steps based on questionnaire results
            updateJourneyStepsFromQuestionnaireResults(data);

            // Show questionnaire results modal
            showQuestionnaireResultsModal(data, systemName);

            if (extractBtn) {
                extractBtn.innerHTML = '<i class="fas fa-check"></i> Results Extracted';
                extractBtn.classList.add('extracted');
                extractBtn.disabled = false;
                extractBtn.style.background = 'var(--neon-purple)';
            }

            // Update compliance progress with questionnaire data
            updateComplianceProgressFromQuestionnaire(data);

        } else {
            alert(`❌ Result Extraction Failed: ${data.message}`);
            if (extractBtn) {
                extractBtn.innerHTML = '<i class="fas fa-download"></i> Extract Results';
                extractBtn.disabled = false;
            }
        }
    })
    .catch(error => {
        console.error('Extraction error:', error);
        alert(`❌ Extraction Error: ${error.message}`);
        if (extractBtn) {
            extractBtn.innerHTML = '<i class="fas fa-download"></i> Extract Results';
            extractBtn.disabled = false;
        }
    });
}

// Update journey steps specifically from questionnaire results
function updateJourneyStepsFromQuestionnaireResults(data) {
    const journeySteps = document.querySelectorAll('.journey-step');

    // Update Gap Analysis step - mark as completed after questionnaire
    const gapAnalysisStep = journeySteps[1]; // Second step
    if (gapAnalysisStep && data.questionnaireCompleted) {
        updateJourneyStepStatus(gapAnalysisStep, 'completed', 100);
        addStepBadge(gapAnalysisStep, '🎯 Questionnaire Complete', 'var(--neon-blue)');
    }

    // Update Recommendations step based on score
    const recommendationsStep = journeySteps[2]; // Third step
    if (recommendationsStep) {
        if (data.complianceScore >= 70) {
            updateJourneyStepStatus(recommendationsStep, 'completed', 100);
            addStepBadge(recommendationsStep, '✅ Recommendations Ready', 'var(--success)');
        } else {
            updateJourneyStepStatus(recommendationsStep, 'in_progress', 80);
            addStepBadge(recommendationsStep, '🔄 Analyzing', 'var(--warning)');
        }
    }

    // Update Re-evaluation step based on score
    const reEvaluationStep = journeySteps[3]; // Fourth step
    if (reEvaluationStep) {
        if (data.complianceScore >= 80) {
            updateJourneyStepStatus(reEvaluationStep, 'completed', 100);
            addStepBadge(reEvaluationStep, '🏆 Excellent Score', 'var(--success)');
        } else if (data.complianceScore >= 60) {
            updateJourneyStepStatus(reEvaluationStep, 'in_progress', 75);
            addStepBadge(reEvaluationStep, '📈 Good Progress', 'var(--neon-blue)');
        } else {
            updateJourneyStepStatus(reEvaluationStep, 'in_progress', 50);
            addStepBadge(reEvaluationStep, '🎯 Improving', 'var(--warning)');
        }
    }

    // Update Report Generation step for high scores
    const reportStep = journeySteps[4]; // Fifth step
    if (reportStep && data.complianceScore >= 75) {
        updateJourneyStepStatus(reportStep, 'in_progress', 60);
        addStepBadge(reportStep, '📄 Report Ready', 'var(--neon-purple)');
    }

    // Show comprehensive progress notification
    showProgressNotification(`🎉 Journey Updated! Compliance Score: ${data.complianceScore.toFixed(1)}% | ${data.summary.matched_controls}/${data.summary.total_controls} controls compliant`);
}

// Update compliance progress from questionnaire data
function updateComplianceProgressFromQuestionnaire(data) {
    // Update overall completion percentage
    const completionElement = document.querySelector('.progress-bar-container .progress-bar');
    if (completionElement) {
        completionElement.style.width = data.complianceScore + '%';

        // Add special glow effect for questionnaire completion
        completionElement.style.boxShadow = '0 0 20px var(--neon-blue), 0 0 40px rgba(0, 212, 255, 0.3)';
        setTimeout(() => {
            completionElement.style.boxShadow = '';
        }, 5000);
    }

    // Update score circle with questionnaire data
    const scoreCircle = document.querySelector('.score-circle span');
    if (scoreCircle) {
        const currentScore = parseInt(scoreCircle.textContent);
        animateScoreChange(scoreCircle, currentScore, data.complianceScore);
    }

    // Update progress statistics
    updateProgressStatistics(data.summary);
}

// Show enhanced questionnaire results modal
function showQuestionnaireResultsModal(data, systemName) {
    const modalHtml = `
        <div id="questionnaireResultsModal" class="modal-overlay" onclick="closeQuestionnaireResults()">
            <div class="modal-content" onclick="event.stopPropagation()">
                <div class="modal-header">
                    <h3><i class="fas fa-chart-line"></i> Questionnaire Results - ${systemName}</h3>
                    <button class="modal-close" onclick="closeQuestionnaireResults()">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="questionnaire-summary">
                        <h4>🎯 Questionnaire Assessment</h4>
                        <div class="score-display">
                            <div class="score-circle-large">
                                <span class="score-number">${data.complianceScore.toFixed(1)}%</span>
                                <span class="score-label">Compliance Score</span>
                            </div>
                            <div class="score-details">
                                <p><strong>Controls Analyzed:</strong> ${data.summary.total_controls}</p>
                                <p><strong>Compliant Controls:</strong> ${data.summary.matched_controls}</p>
                                <p><strong>Improved Controls:</strong> ${data.summary.improved_controls}</p>
                                <p><strong>Questionnaire Status:</strong> 
                                   <span style="color: var(--success);">✅ Completed</span>
                                </p>
                            </div>
                        </div>
                    </div>

                    <div class="journey-progress-section">
                        <h4>🚀 Journey Progress Update</h4>
                        <div class="progress-indicators">
                            <div class="progress-item">
                                <span>Gap Analysis:</span>
                                <span style="color: var(--success);">✅ Completed</span>
                            </div>
                            <div class="progress-item">
                                <span>Recommendations:</span>
                                <span style="color: ${data.complianceScore >= 70 ? 'var(--success)' : 'var(--warning)'};">
                                    ${data.complianceScore >= 70 ? '✅ Ready' : '🔄 In Progress'}
                                </span>
                            </div>
                            <div class="progress-item">
                                <span>Re-evaluation:</span>
                                <span style="color: ${data.complianceScore >= 80 ? 'var(--success)' : 'var(--neon-blue)'};">
                                    ${data.complianceScore >= 80 ? '🏆 Excellent' : '📈 Progressing'}
                                </span>
                            </div>
                        </div>
                    </div>

                    <div class="next-actions">
                        <h4>📋 Recommended Next Steps</h4>
                        <div class="steps-grid">
                            <div class="next-step-card" onclick="navigateToJourneyStep('gap-analysis')">
                                <i class="fas fa-search"></i>
                                <h5>View Gap Analysis</h5>
                                <p>Review detailed analysis results</p>
                            </div>
                            <div class="next-step-card" onclick="navigateToJourneyStep('recommendations')">
                                <i class="fas fa-lightbulb"></i>
                                <h5>Get Recommendations</h5>
                                <p>See improvement suggestions</p>
                            </div>
                            <div class="next-step-card" onclick="navigateToControls()">
                                <i class="fas fa-clipboard-list"></i>
                                <h5>Review Controls</h5>
                                <p>Check individual control status</p>
                            </div>
                            ${data.complianceScore >= 75 ? `
                            <div class="next-step-card" onclick="navigateToReports()">
                                <i class="fas fa-file-alt"></i>
                                <h5>Generate Report</h5>
                                <p>Create compliance report</p>
                            </div>
                            ` : ''}
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-primary" onclick="closeQuestionnaireResults()">Continue</button>
                    <button class="btn btn-success" onclick="navigateToNextJourneyStep(${data.complianceScore})">Next Step</button>
                </div>
            </div>
        </div>
    `;

    // Add modal to body
    document.body.insertAdjacentHTML('beforeend', modalHtml);
}

// Navigate to specific journey step
function navigateToJourneyStep(stepName) {
    closeQuestionnaireResults();
    window.location.href = `/compliance/${stepName}/`;
}

// Navigate to next journey step based on score
function navigateToNextJourneyStep(score) {
    closeQuestionnaireResults();

    if (score >= 80) {
        window.location.href = '/compliance/reports/';
    } else if (score >= 70) {
        window.location.href = '/compliance/re-evaluation/';
    } else if (score >= 60) {
        window.location.href = '/compliance/recommendations/';
    } else {
        window.location.href = '/compliance/gap-analysis/';
    }
}

// Update progress statistics display
function updateProgressStatistics(summary) {
    // Update stat cards if they exist
    const statCards = document.querySelectorAll('.stat-card .stat-number');
    statCards.forEach(card => {
        const label = card.nextElementSibling?.textContent?.toLowerCase();
        if (label?.includes('compliant')) {
            card.textContent = summary.matched_controls;
        } else if (label?.includes('controls')) {
            card.textContent = summary.total_controls;
        }
    });
}

// Enhanced initialization function
function initializeEnhancedQuestionnaireFlow() {
    // Check questionnaire completion on page load
    checkQuestionnaireCompletion();

    // Check every 30 seconds for questionnaire completion
    setInterval(checkQuestionnaireCompletion, 30000);

    // Update journey progress every minute
    setInterval(updateJourneyProgressFromSession, 60000);
}

// Update journey progress from session data
function updateJourneyProgressFromSession() {
    fetch('/compliance/api/journey-progress/')
        .then(response => response.json())
        .then(data => {
            if (data.success && data.journey_updated) {
                // Update overall progress display
                if (data.overall_score > 0) {
                    updateComplianceProgress(data.overall_score, 0);
                }

                // Show notification about updated progress
                if (data.systems_analyzed > 0) {
                    showProgressNotification(`📊 Progress Updated: ${data.systems_analyzed} system(s) analyzed | Overall Score: ${data.overall_score.toFixed(1)}%`);
                }
            }
        })
        .catch(error => console.log('Journey progress update failed:', error));
}
