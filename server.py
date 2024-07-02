import os
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

SENTRY_API_TOKEN = os.getenv('SENTRY_API_TOKEN')
SENTRY_ORG_SLUG = os.getenv('SENTRY_ORG_SLUG')
DEFAULT_CRITICAL_ERROR_THRESHOLD = int(os.getenv('DEFAULT_CRITICAL_ERROR_THRESHOLD', 100))
DEFAULT_WARNING_ERROR_THRESHOLD = int(os.getenv('DEFAULT_WARNING_ERROR_THRESHOLD', 50))
DEFAULT_CRITICAL_PERFORMANCE_THRESHOLD = int(os.getenv('DEFAULT_CRITICAL_PERFORMANCE_THRESHOLD', 500))
DEFAULT_WARNING_PERFORMANCE_THRESHOLD = int(os.getenv('DEFAULT_WARNING_PERFORMANCE_THRESHOLD', 200))


HEADERS = {
    'Authorization': f'Bearer {SENTRY_API_TOKEN}',
    'Content-Type': 'application/json'
}

@app.route('/create_project', methods=['POST'])
def create_project():
    data = request.json
    project_name = data.get('project_name')
    team_slug = data.get('team_slug')
    platform = data.get('platform')
    critical_error_threshold = data.get('critical_error_rate_threshold', DEFAULT_CRITICAL_ERROR_THRESHOLD)
    warning_error_threshold = data.get('warning_error_rate_threshold', DEFAULT_WARNING_ERROR_THRESHOLD)
    critical_performance_threshold = data.get('critical_performance_throughput_threshold', DEFAULT_CRITICAL_PERFORMANCE_THRESHOLD)
    warning_performance_threshold = data.get('warning_performance_throughput_threshold', DEFAULT_WARNING_PERFORMANCE_THRESHOLD)

    sentry_api_url = f'https://sentry.io/api/0/teams/{SENTRY_ORG_SLUG}/{team_slug}/projects/'
    project_slug = project_name.lower().replace(' ', '-')
    project_response = requests.post(
        sentry_api_url,
        headers=HEADERS,
        json={'name': project_name, 'slug': project_slug, 'platform': platform}
    )

    if project_response.status_code != 201:
        return jsonify({'error': 'Failed to create project'}), project_response.status_code

    # Create error rate alert
    create_metric_alert(project_slug, 'Number of Errors', 'event.type:error is:unresolved', critical_error_threshold, warning_error_threshold)

    # Create performance throughput alert
    create_metric_alert(project_slug, 'Performance Throughput', '', critical_performance_threshold, warning_performance_threshold, 'transactions')

    return jsonify({'message': 'Project and alerts created successfully'}), 201

def create_metric_alert(project_slug, alert_name, query, critical_threshold, warning_threshold, metric_type='events'):

    alert_payload = {
        'name': alert_name,
        "queryType": 0 if metric_type == "events" else 1,
        "dataset": metric_type,
        "projects": [f'{project_slug}'],
        "aggregate": "count()",
        "timeWindow": 60,
        "thresholdType": 0, # 0 - Above, 1 - Below
        "query": "is:unresolved" if metric_type == "events" else "",
        "eventTypes": ["error", "default"] if metric_type == "events" else [],
        "triggers": [
            {
                "label": "critical",
                "alertThreshold": critical_threshold,
                "actions": []
            },
            {
                "label": "warning",
                "alertThreshold": warning_threshold,
                "actions": []
            }
        ],
    }

    sentry_api_url = f'https://sentry.io/api/0/organizations/{SENTRY_ORG_SLUG}/alert-rules/'
    response = requests.post(
        sentry_api_url,
        headers=HEADERS,
        json=alert_payload
    )

    if response.status_code != 201:
        print(f'Failed to create alert: {alert_name} for project: {project_slug}')

if __name__ == '__main__':
    app.run(debug=True)