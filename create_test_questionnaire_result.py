#!/usr/bin/env python
"""
Script to create test questionnaire results for debugging
"""
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append('C:\\Users\\Jihed\\PycharmProjects\\CAAS_App')

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'compliance_project.settings')
django.setup()

from django.contrib.auth.models import User
from compliance.models import QuestionnaireResult

def create_test_questionnaire_result():
    """Create a test questionnaire result for the current user"""

    # Get the first user (you can modify this to target a specific user)
    try:
        user = User.objects.first()
        if not user:
            print("❌ No users found in database. Please create a user first.")
            return

        print(f"Creating test questionnaire result for user: {user.username}")

        # Create test questionnaire result
        result, created = QuestionnaireResult.objects.get_or_create(
            user=user,
            session_id=f"test_session_{user.id}",
            defaults={
                'overall_score': 75,
                'maturity_level': 'defined',
                'risk_level': 'medium',
                'category_scores': {
                    'access_control': 80,
                    'data_protection': 70,
                    'network_security': 75,
                    'incident_response': 65,
                    'risk_management': 85
                },
                'framework_recommendations': [
                    'ISO 27001',
                    'NIS2 Directive',
                    'IEC 62443'
                ],
                'gap_analysis': {
                    'critical_gaps': {
                        'description': 'Missing incident response procedures',
                        'severity': 'high',
                        'impact_score': 8,
                        'actions': [
                            {
                                'title': 'Develop incident response plan',
                                'description': 'Create comprehensive incident response procedures'
                            }
                        ]
                    },
                    'access_control': {
                        'description': 'Incomplete access control policies',
                        'severity': 'medium',
                        'impact_score': 6,
                        'actions': [
                            {
                                'title': 'Review access control policies',
                                'description': 'Update and strengthen access control measures'
                            }
                        ]
                    }
                },
                'priority_actions': [
                    {
                        'title': 'Implement Multi-Factor Authentication',
                        'description': 'Deploy MFA across all critical systems',
                        'priority': 'high',
                        'effort': 'Medium',
                        'timeline': '2-4 weeks',
                        'score_impact': 15,
                        'category': 'Access Control'
                    },
                    {
                        'title': 'Establish Security Monitoring',
                        'description': 'Set up 24/7 security monitoring and alerting',
                        'priority': 'high',
                        'effort': 'High',
                        'timeline': '4-6 weeks',
                        'score_impact': 20,
                        'category': 'Monitoring'
                    },
                    {
                        'title': 'Update Data Classification',
                        'description': 'Classify all organizational data assets',
                        'priority': 'medium',
                        'effort': 'Medium',
                        'timeline': '3-4 weeks',
                        'score_impact': 10,
                        'category': 'Data Protection'
                    }
                ],
                'raw_responses': {
                    'q1_access_control': 'partially_implemented',
                    'q2_data_encryption': 'implemented',
                    'q3_incident_response': 'not_implemented',
                    'q4_security_training': 'implemented',
                    'q5_vulnerability_management': 'partially_implemented'
                }
            }
        )

        if created:
            print("✅ Test questionnaire result created successfully!")
        else:
            print("ℹ️ Test questionnaire result already exists, updating...")
            # Update existing result
            result.overall_score = 75
            result.maturity_level = 'defined'
            result.risk_level = 'medium'
            result.save()
            print("✅ Test questionnaire result updated successfully!")

        print(f"""
📊 QUESTIONNAIRE RESULT SUMMARY:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
User: {result.user.username}
Overall Score: {result.overall_score}%
Maturity Level: {result.get_maturity_level_display()}
Risk Level: {result.get_risk_level_display()}
Session ID: {result.session_id}
Created: {result.completed_at}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 PRIORITY ACTIONS: {len(result.priority_actions)}
📈 CATEGORY SCORES: {len(result.category_scores)} categories
🔍 GAP ANALYSIS: {len(result.gap_analysis)} areas identified
📋 FRAMEWORK RECOMMENDATIONS: {len(result.framework_recommendations)} frameworks

Now you can view the questionnaire results in your dashboard!
""")

    except Exception as e:
        print(f"❌ Error creating test questionnaire result: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    create_test_questionnaire_result()
