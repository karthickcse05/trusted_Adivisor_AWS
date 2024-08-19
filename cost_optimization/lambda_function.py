import boto3
import pandas as pd
#from tabulate import tabulate
import logging
import json
import os
import sys
import re

# Initialize AWS clients
session = boto3.Session()
trusted_advisor_client = session.client('support')
sns_client = session.client('sns')
ses_client = session.client('ses')
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Function to get Trusted Advisor recommendations
def get_trusted_advisor_recommendations():
    response = trusted_advisor_client.describe_trusted_advisor_checks(language='en')
    checks = response['checks']
    cost_optimization_checks = [check for check in checks if check['category'] == 'cost_optimizing']
    
    recommendations = []
    for check in cost_optimization_checks:
        check_id = check['id']
        check_result = trusted_advisor_client.describe_trusted_advisor_check_result(checkId=check_id)
        # Check if 'flaggedResources' key exists in the result
        if 'flaggedResources' in check_result['result']:
            flagged_resources = check_result['result']['flaggedResources']
            for resource in flagged_resources:
                recommendations.append({
                    'check_name': check['name'],
                    'resource_id': resource['resourceId'],
                    'status': resource['status'],
                    'Description':check['description'],
                    'metadata': [item for item in resource['metadata'] if item is not None]  # Filter out None values
                })
        else:
            logger.warning(f"No flagged resources for check: {check['name']}")
    
    return recommendations

# Function to format metadata into tabular format
def format_metadata(metadata, columns):
    df = pd.DataFrame(metadata, columns=columns)
    return  df.to_html(index=False)
    #return tabulate(df, headers='keys', tablefmt='firstrow')

# Function to send email using SES
def send_email(subject, body, to_addresses):
    response = ses_client.send_email(
        Source=os.environ.get['FROM_ADDRESS'],
        Destination={
            'ToAddresses': to_addresses
        },
        Message={
            'Subject': {
                'Data': subject
            },
            'Body': {
                'Html': {
                    'Data': body
                }
            }
        }
    )
    return response

def extract_description(html_content):
    # Use a regular expression to find the content up to "Alert Criteria"
    match = re.search(r'(.*?)<h4 class=\'headerBodyStyle\'>Alert Criteria</h4>', html_content, re.DOTALL)
    if match:
        return match.group(1).strip()
    else:
        return None
    
# Main function
def get_cost_optimization_recommendations():
    recommendations = get_trusted_advisor_recommendations()
    
    email_body = ""
    html_table = """<html><body><h2>AWS Trusted Advisor Cost Optimization Recommendations</h2>"""
    # Group recommendations by check name
    grouped_recommendations = {}
    for recommendation in recommendations:
        check_name = recommendation['check_name']
        if check_name not in grouped_recommendations:
            grouped_recommendations[check_name] = []
        grouped_recommendations[check_name].append(recommendation)

    for check_name, recs in grouped_recommendations.items():
        metadata = []
        if check_name == 'Idle Load Balancers':
             html_table += """<h3>Idle Load Balancers</h3>"""
             #print(extract_description(recs[0]['Description']))
             html_table += f"<p>{extract_description(recs[0]['Description'])}</p>"
             #html_table += """<p>recs[0]['Description']<p>"""
             columns = ['region', 'load balancer name', 'reason', 'estimated monthly savings']
             for rec in recs:
                metadata.append(rec['metadata'])
             html_table += format_metadata(metadata, columns)
        elif check_name == 'Amazon RDS Idle DB Instances':
             html_table += """<h3>Amazon RDS Idle DB Instances</h3>"""
             html_table += f"<p>{extract_description(recs[0]['Description'])}</p>"
             columns = ['region', 'DB Instance name', 'Multi AZ', 'Instance type', 'Stored Provisioned(GB)', 'Days since last connection', 'estimated monthly savings']
             for rec in recs:
                metadata.append(rec['metadata'])
             html_table += format_metadata(metadata, columns)
        elif check_name == 'Low Utilization Amazon EC2 Instances':
             html_table += """<h3>Low Utilization Amazon EC2 Instances</h3>"""
             html_table += f"<p>{extract_description(recs[0]['Description'])}</p>"
             columns = ['Region/AZ', 'Instance ID', 'Instance Name', 'Instance Type', 'Estimated Monthly Savings']
             for rec in recs:
                metadata.append(rec['metadata'][:5])
             html_table += format_metadata(metadata, columns)
        elif check_name == 'Underutilized Amazon EBS Volumes':
             html_table += """<h3>Underutilized Amazon EBS Volumes</h3>"""
             html_table += f"<p>{extract_description(recs[0]['Description'])}</p>"
             columns = ['Region', 'Volume ID', 'Volume Name', 'Volume Type', 'Volume Size', 'Monthly Storage Cost']
             for rec in recs:
                metadata.append(rec['metadata'][:6])
             html_table += format_metadata(metadata, columns)
        elif check_name == 'AWS Lambda Functions with Excessive Timeouts':
             html_table += """<h3>AWS Lambda Functions with Excessive Timeouts</h3>"""
             html_table += f"<p>{extract_description(recs[0]['Description'])}</p>"
             columns = ['Status', 'Region', 'Function ARN']
             for rec in recs:
                metadata.append(rec['metadata'][:3])
             html_table += format_metadata(metadata, columns)
        elif check_name == 'AWS Lambda Functions with High Error Rates':
             html_table += """<h3>AWS Lambda Functions with High Error Rates</h3>"""
             html_table += f"<p>{extract_description(recs[0]['Description'])}</p>"
             columns = ['Status', 'Region', 'Function ARN']
             for rec in recs:
                metadata.append(rec['metadata'][:3])
             html_table += format_metadata(metadata, columns)
        elif check_name == 'Amazon EBS over-provisioned volumes':
             html_table += """<h3>Amazon EBS over-provisioned volumes</h3>"""
             html_table += f"<p>{extract_description(recs[0]['Description'])}</p>"
             columns = ['Status', 'Region', 'Volume ID','Volume Type','Volume Size(GB)']
             for rec in recs:
                metadata.append(rec['metadata'][:5])
             html_table += format_metadata(metadata, columns)
        elif check_name == 'Amazon EC2 instances consolidation for Microsoft SQL Server':
             html_table += """<h3>Amazon EC2 instances consolidation for Microsoft SQL Server</h3>"""
             html_table += f"<p>{extract_description(recs[0]['Description'])}</p>"
             columns = ['Status', 'Region', 'Instance ID','Instance Type']
             for rec in recs:
                metadata.append(rec['metadata'][:4])
             html_table += format_metadata(metadata, columns)
        elif check_name == 'Amazon EC2 instances over-provisioned for Microsoft SQL Server':
             html_table += """<h3>Amazon EC2 instances over-provisioned for Microsoft SQL Server</h3>"""
             html_table += f"<p>{extract_description(recs[0]['Description'])}</p>"
             columns = ['Status', 'Region', 'Instance ID','Instance Type']
             for rec in recs:
                metadata.append(rec['metadata'][:4])
             html_table += format_metadata(metadata, columns)
        elif check_name == 'AWS Lambda over-provisioned functions for memory size':
             html_table += """<h3>AWS Lambda over-provisioned functions for memory size</h3>"""
             html_table += f"<p>{extract_description(recs[0]['Description'])}</p>"
             columns = ['Status', 'Region', 'Function Name']
             for rec in recs:
                metadata.append(rec['metadata'][:3])
             html_table += format_metadata(metadata, columns)
        elif check_name == 'Amazon Route 53 Latency Resource Record Sets':
             html_table += """<h3>Amazon Route 53 Latency Resource Record Sets</h3>"""
             html_table += f"<p>{extract_description(recs[0]['Description'])}</p>"
             columns = ['Hosted Zone Name', 'Hosted Zone ID']
             for rec in recs:
                metadata.append(rec['metadata'][:2])
             html_table += format_metadata(metadata, columns)
        elif check_name == 'Amazon EC2 Reserved Instance Lease Expiration':
             html_table += """<h3>Amazon EC2 Reserved Instance Lease Expiration</h3>"""
             html_table += f"<p>{extract_description(recs[0]['Description'])}</p>"
             columns = ['Status', 'Zone', 'Instance Type','Platform','Instance Count','Current Monthly Cost','Estimated Monthly Savings']
             for rec in recs:
                metadata.append(rec['metadata'][:7])
             html_table += format_metadata(metadata, columns)
        elif check_name == 'Amazon Comprehend Underutilized Endpoints':
             html_table += """<h3>Amazon Comprehend Underutilized Endpoints</h3>"""
             html_table += f"<p>{extract_description(recs[0]['Description'])}</p>"
             columns = ['Status', 'Region', 'Endpoint ARN']
             for rec in recs:
                metadata.append(rec['metadata'][:3])
             html_table += format_metadata(metadata, columns)
        elif check_name == 'Unassociated Elastic IP Addresses':
             html_table += """<h3>Unassociated Elastic IP Addresses</h3>"""
             html_table += f"<p>{extract_description(recs[0]['Description'])}</p>"
             columns = ['Region', 'IP Address']
             for rec in recs:
                metadata.append(rec['metadata'])
             html_table += format_metadata(metadata, columns)
        elif check_name == 'Underutilized Amazon Redshift Clusters':
             html_table += """<h3>Underutilized Amazon Redshift Clusters</h3>"""
             html_table += f"<p>{extract_description(recs[0]['Description'])}</p>"
             columns = ['Status', 'Region','Cluster','Instance Type','Reason','Estimated Monthly Savings']
             for rec in recs:
                metadata.append(rec['metadata'])
             html_table += format_metadata(metadata, columns)
        elif check_name == 'Inactive AWS Network Firewall':
             html_table += """<h3>Inactive AWS Network Firewall</h3>"""
             html_table += f"<p>{extract_description(recs[0]['Description'])}</p>"
             columns = ['Status', 'Region','Network Firewall Arn','VPC ID']
             for rec in recs:
                metadata.append(rec['metadata'][:4])
             html_table += format_metadata(metadata, columns)
        elif check_name == 'Inactive NAT Gateways':
             html_table += """<h3>Inactive NAT Gateways</h3>"""
             ##print(recs[0]['Description'])
             html_table += """<p>Checks your NAT Gateways for any gateways that appear to be inactive. A NAT Gateway is considered to be inactive if it had no data processed in the last 30 days.  NAT Gateways have hourly charges and data processed charges.  This check alerts you to NAT Gateway with 0  data processed in the last 30 days.</p>"""
             columns = ['Status', 'Region','NAT Gateway ID','Subnet ID','VPC ID']
             for rec in recs:
                metadata.append(rec['metadata'][:5])
             html_table += format_metadata(metadata, columns)
        else:
            continue
    
    # Send email
    html_table += "</body></html>"
    send_email(
        subject="AWS Trusted Advisor Cost Optimization Recommendations",
        body=html_table,
        to_addresses=os.environ.get['TO_ADDRESS']   #['karthickcse05@gmail.com']
    )

 def lambda_handler(event, context):
     get_cost_optimization_recommendations()
     return {
         'statusCode': 200,
         'body': json.dumps('Hello from Lambda!')
     }

#if __name__ == "__main__":
#    get_cost_optimization_recommendations()
