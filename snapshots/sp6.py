#!/Library/Frameworks/Python.framework/Versions/3.10/bin/python
import boto3
import csv
import os
from datetime import datetime, timedelta

# The name of the S3 bucket to store the report
bucket_name = 'kshdflk8ksajdlkfsa'

# The AWS regions to check
regions = ['us-west-1', 'us-west-2', 'us-east-1', 'eu-west-1']

# The AWS accounts to check
accounts = ['default']

# The tag to check for snapshots without a Name tag
missing_name_tag = 'ExpirationDate'

# The number of days until the snapshots expire and are deleted
expiration_days = 0

# Generate a unique report filename based on the current date and time
now = datetime.now()
report_date = now.strftime('%Y-%m-%d-%H-%M-%S')
report_filename = f'snapshot-report-{report_date}.csv'
deletion_report_filename = f'snapshot-deletion-report-{report_date}.csv'

# Create an S3 client
s3_client = boto3.client('s3')

# Create a CSV writer for Availabile Snapshots
csv_file = open('/tmp/report.csv', 'w', newline='')
csv_writer = csv.writer(csv_file)
csv_writer.writerow(['Account', 'Snapshot ID', 'Region', 'StartTime', 'Volume ID', 'Tags', 'Expiration'])

# Create a CSV writer deletion report
csv_deletion_file = open('/tmp/deletion_report.csv', 'w', newline='')
csv_deletion_writer = csv.writer(csv_deletion_file)
csv_deletion_writer.writerow(['Account', 'Snapshot ID', 'Region', 'StartTime', 'Volume ID', 'Tags', 'Expiration','Status'])

# Calculate the expiration date for snapshots
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

        # Get information about all snapshots in the region
        response = ec2_client.describe_snapshots(OwnerIds=['self'])

        # Loop through each snapshot in the response
        print("Snapshots in Account -", account, region)
        for snapshot in response['Snapshots']:
            snapshot_id = snapshot['SnapshotId']
            snapshot_start_time = snapshot['StartTime']
            print(snapshot_id)

            # Check if the snapshot is missing the Name tag
            missing_name_tag_flag = True
            for tag in snapshot.get('Tags', []):
                if tag['Key'] == 'Name' and tag['Value'] == 'snappy.me':
                    missing_name_tag_flag = False
                    break

            # If the snapshot is missing the Name tag, tag it and add it to the report
            if missing_name_tag_flag:
                # Tag the snapshot with the TTL tag and expiration date
                ec2_client.create_tags(
                    Resources=[snapshot_id],
                    Tags=[
                        {'Key': missing_name_tag, 'Value': expiration_date.isoformat()}
                    ]
                )

                # Add the snapshot to the report
                volume_id = snapshot['VolumeId']
                snapshot_data = [
                    account,
                    snapshot_id,
                    region,
                    snapshot_start_time.isoformat(),
                    volume_id,
                    str(snapshot.get('Tags', [])),
                    expiration_date.isoformat()
                ]
                csv_writer.writerow(snapshot_data)
            
            if not missing_name_tag_flag:
                # Add the snapshot to the report
                volume_id = snapshot['VolumeId']
                snapshot_data = [
                    account,
                    snapshot_id,
                    region,
                    snapshot_start_time.isoformat(),
                    volume_id,
                    str(snapshot.get('Tags', [])),
                    'null'
                ]
                csv_writer.writerow(snapshot_data)

            
            tags = snapshot.get('Tags', [])
            #print(tags)
            expiration_tag = next((tag for tag in tags if tag['Key'] == 'ExpirationDate'), None)
            #print(expiration_tag)
            if expiration_tag is not None:
                expiration_date_str = expiration_tag['Value']
                expiration_date = datetime.fromisoformat(expiration_date_str)
                if expiration_date <= now:
                    #If the volume has expired, delete it and add it to the report
                    #ec2_client.delete_volume(VolumeId=volume_id)
                    ec2_client.delete_snapshot(SnapshotId=snapshot_id)
                    volume_id = snapshot['VolumeId']
                    snapshot_data = [
                        account,
                        snapshot_id,
                        region,
                        snapshot_start_time.isoformat(),
                        volume_id,
                        str(snapshot.get('Tags', [])),
                        expiration_date.isoformat(),
                        # volume_id,
                        ## region,
                        # volume['CreateTime'].isoformat(),
                        # str(volume['Size']),
                        # str(volume['Encrypted']),
                        # str(volume.get('Tags', [])),
                        # expiration_date.isoformat(),
                        "Deleted"
                    ]
                    print("Deleting the Snapshot(s) as it has expired\n", snapshot_data)
                    csv_deletion_writer.writerow(snapshot_data)


# Close the CSV file
csv_file.close()
csv_deletion_file.close()

# Upload the report to the S3 bucket
s3_client.upload_file('/tmp/report.csv', bucket_name, 'snapshot_report/' + report_filename)
s3_client.upload_file('/tmp/deletion_report.csv', bucket_name, 'snapshot_report/' + deletion_report_filename)

# Delete the local report file
os.remove('/tmp/report.csv')
os.remove('/tmp/deletion_report.csv')

# Print the S3 URL of the Available report
report_url = f's3://{bucket_name}/snapshot_report/{report_filename}'
print(f'Report URL: {report_url}')

# Print the S3 URL of the report
deletion_report_url = f's3://{bucket_name}/snapshot_report/{deletion_report_filename}'
print(f'Deletion Report URL: {deletion_report_url}')