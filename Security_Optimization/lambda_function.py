import boto3
import pandas as pd
import os
#from tabulate import tabulate
import logging



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
    security_optimization_checks = [check for check in checks if check['category'] == 'security']
    
    recommendations = []
    for check in security_optimization_checks:
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
        Source=os.environ.get['FROM_ADDRESS'],,
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


# Main function
def get_security_optimization_recommendations():
    recommendations = get_trusted_advisor_recommendations()
    
    email_body = ""
    html_table = """<html><body><h2>AWS Trusted Advisor Security Recommendations</h2>"""
    # Group recommendations by check name
    grouped_recommendations = {}
    for recommendation in recommendations:
        check_name = recommendation['check_name']
        if check_name not in grouped_recommendations:
            grouped_recommendations[check_name] = []
        grouped_recommendations[check_name].append(recommendation)

    for check_name, recs in grouped_recommendations.items():
        metadata = []
        if check_name == 'Amazon EC2 instances with Microsoft Windows Server end of support':
             html_table += """<h3>Amazon EC2 instances with Microsoft Windows Server end of support</h3>"""
             columns = ['Status', 'Region', 'Instance ID', 'Windows Server Version','Support Cycle','End of Support']
             for rec in recs:
                metadata.append(rec['metadata'][:6])
             html_table += format_metadata(metadata, columns)
        elif check_name == 'Amazon EC2 instances with Ubuntu LTS end of standard support':
             html_table += """<h3>Amazon EC2 instances with Ubuntu LTS end of standard support</h3>"""
             columns = ['Status', 'Region', 'Ubuntu Lts Version', 'Expected End Of Support Date','Instance Id','Support Cycle']
             for rec in recs:
                metadata.append(rec['metadata'][:6])
             html_table += format_metadata(metadata, columns)
        elif check_name == 'Amazon RDS storage encryption is turned off':
             html_table += """<h3>Amazon RDS storage encryption is turned off</h3>"""
             columns = ['Status', 'Region', 'Resource', 'Engine Name']
             for rec in recs:
                metadata.append(rec['metadata'][:4])
             html_table += format_metadata(metadata, columns)
        elif check_name == 'AWS Lambda Functions Using Deprecated Runtimes':
             html_table += """<h3>AWS Lambda Functions Using Deprecated Runtimes</h3>"""
             columns = ['Status', 'Region', 'Function ARN', 'Runtime', 'Days to Deprecation', 'Deprecation Date','Average Daily Invokes']
             for rec in recs:
                metadata.append(rec['metadata'][:7])
             html_table += format_metadata(metadata, columns)
        elif check_name == 'ELB Listener Security':
             html_table += """<h3>ELB Listener Security</h3>"""
             columns = ['Region', 'Load Balancer Name']
             for rec in recs:
                metadata.append(rec['metadata'][:2])
             html_table += format_metadata(metadata, columns)
        # elif check_name == 'Security Groups - Specific Ports Unrestricted':
        #      html_table += """<h3>Security Groups - Specific Ports Unrestricted</h3>"""
        #      columns = ['Region', 'Security Group Name', 'Security Group ID','Protocol']
        #      for rec in recs:
        #         metadata.append(rec['metadata'][:4])
        #      html_table += format_metadata(metadata, columns)
        # elif check_name == 'Security Groups - Unrestricted Access':
        #      html_table += """<h3>Security Groups - Unrestricted Access</h3>"""
        #      columns = ['Region', 'Security Group Name', 'Security Group ID','Protocol']
        #      for rec in recs:
        #         metadata.append(rec['metadata'][:4])
        #      html_table += format_metadata(metadata, columns)
        elif check_name == 'Amazon S3 Bucket Permissions':
             html_table += """<h3>Amazon S3 Bucket Permissions</h3>"""
             columns = ['Region','Region API Parameter', 'Bucket Name', 'ACL Allows List','ACL Allows Upload/Delete','Status','Policy Allows Access']
             for rec in recs:
                metadata.append(rec['metadata'])
             html_table += format_metadata(metadata, columns)
        elif check_name == 'Amazon EBS Public Snapshots':
             html_table += """<h3>Amazon EBS Public Snapshots</h3>"""
             columns = ['Status', 'Region', 'Volume ID','Snapshot ID']
             for rec in recs:
                metadata.append(rec['metadata'][:4])
             html_table += format_metadata(metadata, columns)
        elif check_name == 'Amazon EC2 instances with Microsoft SQL Server end of support':
             html_table += """<h3>Amazon EC2 instances with Microsoft SQL Server end of support</h3>"""
             columns = ['Status', 'Region', 'Instance ID', 'SQL Server Version','Support Cycle','End of Support']
             for rec in recs:
                metadata.append(rec['metadata'][:6])
             html_table += format_metadata(metadata, columns)
        elif check_name == 'Amazon RDS Aurora storage encryption is turned off':
             html_table += """<h3>Amazon RDS Aurora storage encryption is turned off</h3>"""
             columns = ['Status', 'Region', 'Resource','Engine Name']
             for rec in recs:
                metadata.append(rec['metadata'][:4])
             html_table += format_metadata(metadata, columns)
        elif check_name == 'Amazon RDS Public Snapshots':
             html_table += """<h3>Amazon RDS Public Snapshots</h3>"""
             columns = ['Status', 'Region', 'DB Instance or Cluster ID','Snapshot ID']
             for rec in recs:
                metadata.append(rec['metadata'])
             html_table += format_metadata(metadata, columns)
        elif check_name == 'A WAF global rule group should have at least one rule':
             html_table += """<h3>A WAF global rule group should have at least one rule</h3>"""       
             columns = ['Status', 'Region', 'Resource']
             for rec in recs:
                metadata.append(rec['metadata'][:3])
             html_table += format_metadata(metadata, columns)
        elif check_name == 'Amazon DocumentDB clusters should be encrypted at rest':
             html_table += """<h3>Amazon DocumentDB clusters should be encrypted at rest</h3>"""
             columns = ['Status', 'Region', 'Resource']
             for rec in recs:
                metadata.append(rec['metadata'][:3])
             html_table += format_metadata(metadata, columns)
        elif check_name == 'Amazon EC2 instances launched using Auto Scaling group launch configurations should not have Public IP addresses':
             html_table += """<h3>Amazon EC2 instances launched using Auto Scaling group launch configurations should not have Public IP addresses</h3>"""
             columns = ['Status', 'Region', 'Resource']
             for rec in recs:
                metadata.append(rec['metadata'][:3])
             html_table += format_metadata(metadata, columns)
        elif check_name == 'ACM certificates should be renewed after a specified time period':
             html_table += """<h3>ACM certificates should be renewed after a specified time period</h3>"""
             columns = ['Status', 'Region', 'Resource']
             for rec in recs:
                metadata.append(rec['metadata'][:3])
             html_table += format_metadata(metadata, columns)
        elif check_name == 'Amazon DocumentDB manual cluster snapshots should not be public':
             html_table += """<h3>Amazon DocumentDB manual cluster snapshots should not be public</h3>"""
             columns = ['Status', 'Region', 'Resource']
             for rec in recs:
                metadata.append(rec['metadata'][:3])
             html_table += format_metadata(metadata, columns)
        else:
            continue
    
    # Send email
    html_table += "</body></html>"
    send_email(
        subject="AWS Trusted Advisor Security Recommendations",
        body=html_table,
        to_addresses=os.environ.get['TO_ADDRESS']   #['karthickcse05@gmail.com']
    )

 def lambda_handler(event, context):
     get_security_optimization_recommendations()
     return {
         'statusCode': 200,
         'body': json.dumps('Hello from Lambda!')
     }

#if __name__ == "__main__":
#    get_security_optimization_recommendations()
