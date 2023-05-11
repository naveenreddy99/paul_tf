#!/Library/Frameworks/Python.framework/Versions/3.10/bin/python
import boto3
import csv
import os
from datetime import datetime, timedelta

def lambda_handler(event, context):
    # The name of the S3 bucket to store the report
    bucket_name = 'kshdflk8ksajdlkfsa'

    # The AWS regions to check
    regions = ['us-west-1', 'us-west-2', 'us-east-1', 'eu-west-1', 'us-east-2']

    # The AWS accounts to check
    accounts = ['default']   #['ice-cloud-mgmt','ice-prod','maa-nonprod','hsi-nonprod','ero-nonprod','ero-prod']

    # The number of days until the available volumes expire and are deleted
    expiration_days = 0

    # Generate a unique report filename based on the current date and time
    now = datetime.now()
    report_date = now.strftime('%Y-%m-%d-%H-%M-%S')
    report_filename = f'ec2-volume-available-report-{report_date}.csv'
    deletion_report_filename = f'ec2-volume-deletion-report-{report_date}.csv'

    # Create an S3 client
    s3_client = boto3.client('s3')

    # Create a CSV writer availablity report
    csv_file = open('/tmp/report.csv', 'w', newline='')
    csv_writer = csv.writer(csv_file)
    csv_writer.writerow(['Account', 'Volume ID', 'Region', 'CreateTime', 'Size', 'Encrypted', 'Tags', 'Expiration', 'Status'])

    # Create a CSV writer deletion report
    csv_deletion_file = open('/tmp/deletion_report.csv', 'w', newline='')
    csv_deletion_writer = csv.writer(csv_deletion_file)
    csv_deletion_writer.writerow(['Account', 'Volume ID', 'Region', 'CreateTime', 'Size', 'Encrypted', 'Tags', 'Expiration', 'Status'])


    # Calculate the expiration date for available volumes
    expiration_date = now + timedelta(days=expiration_days)

    # Loop through each AWS account and region combination
    for account in accounts:
        for region in regions:

            # Create a session for the account and region
            session = boto3.Session(
                region_name=region,
                profile_name=f'{account}'
            )

            # Create an EC2 client using the session
            ec2_client = session.client('ec2')

            # Get information about all volumes in the region
            response = ec2_client.describe_volumes()

            # Loop through each volume in the response
            print("Volumes in Account -", account, region)
            for volume in response['Volumes']:
                volume_id = volume['VolumeId']
                volume_state = volume['State']
                print(volume_id, volume_state)

                # If the volume is available, add it to the report and tag it
                if volume_state == 'available':
                    volume_data = [
                        account,
                        volume_id,
                        region,
                        volume['CreateTime'].isoformat(),
                        str(volume['Size']),
                        str(volume['Encrypted']),
                        str(volume.get('Tags', [])),
                        expiration_date.isoformat(),
                        volume_state
                    ]
                    csv_writer.writerow(volume_data)

                    # Tag the volume with the expiration date tag
                    ec2_client.create_tags(
                        Resources=[volume_id],
                        Tags=[{'Key': 'ExpirationDate', 'Value': expiration_date.isoformat()}]
                    )

                # If the volume is in available state, check its tags for the expiration date
                #elif volume_state == 'available':
                    tags = volume.get('Tags', [])
                    expiration_tag = next((tag for tag in tags if tag['Key'] == 'ExpirationDate'), None)
                    if expiration_tag is not None:
                        expiration_date_str = expiration_tag['Value']
                        expiration_date = datetime.fromisoformat(expiration_date_str)
                        if expiration_date <= now and volume_state == 'available':
                            # If the volume has expired, delete it and add it to the report
                            ec2_client.delete_volume(VolumeId=volume_id)
                            volume_data = [
                                account,
                                volume_id,
                                region,
                                volume['CreateTime'].isoformat(),
                                str(volume['Size']),
                                str(volume['Encrypted']),
                                str(volume.get('Tags', [])),
                                expiration_date.isoformat(),
                                "Deleted"
                            ]
                            print("Deleting the volume(s) as it has expired", volume_data)
                            csv_deletion_writer.writerow(volume_data)

    # Close the CSV file
    csv_file.close()
    csv_deletion_file.close()

    # Upload the report to the S3 bucket
    s3_client.upload_file('/tmp/report.csv', bucket_name, 'volume_report/' + report_filename)
    s3_client.upload_file('/tmp/deletion_report.csv', bucket_name, 'volume_report/' + deletion_report_filename)

    # Delete the local report file
    os.remove('/tmp/report.csv')
    os.remove('/tmp/deletion_report.csv')

    # Print the S3 URL of the report
    report_url = f's3://{bucket_name}/volume_report/{report_filename}'
    print(f'Report URL: {report_url}')

    # Print the S3 URL of the report
    deletion_report_url = f's3://{bucket_name}/volume_report/{deletion_report_filename}'
    print(f'Deletion Report URL: {deletion_report_url}')