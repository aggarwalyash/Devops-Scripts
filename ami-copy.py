import boto3

target_account_id = '339712959886'
source_profile = 'old-account'
role_on_target_account = 'arn:aws:iam::339712959886:role/ami-copy-custom-role'
source_region = 'ap-south-1'
target_region = 'ap-south-1'

def remove_aws_tags(tags_list):
    filtered_tags = []
    for tag in tags_list:
        if not tag['Key'].startswith('aws:'):
            filtered_tags.append(tag)
    return filtered_tags

def get_main_session():
    """
    This function returns the main session of the Master/Mgmt account.
    """
    session = boto3.Session(profile_name=source_profile, region_name=source_region)
    return session

def get_temp_cred(session, role_arn, account_id):
    """
    This function returns the temporary credentials using the trust
    relationship
    """
    get_cred_client = session.client('sts')
    get_cred_response = get_cred_client.assume_role(\
        RoleArn=role_arn,
        RoleSessionName=account_id)
    return get_cred_response['Credentials']


def get_temp_session(cred, region):
    """
    This function returns the temporary session, using the temporary
    AccessKeyId, SecretAccessKey and the SessionToken returned by the
    temporary credentials
    """
    temp_session = boto3.Session(\
        aws_access_key_id=cred['AccessKeyId'],
        aws_secret_access_key=cred['SecretAccessKey'],
        aws_session_token=cred['SessionToken'],
        region_name=region)
    return temp_session


def add_launch_permission(session, region):
    """
    This function reurns the list of filtered AMI 
    """

    ec2 = session.resource('ec2', region_name = region)
    images = ec2.images.filter(Owners=['385461722744'], ImageIds=['ami-0bb74fe6b21953b30'])
    
    # filtered_images = ec2.images.filter(Owners=['385461722744'], ImageIds=['ami-05ecf9ab27a5aac84'])
    # for image in filtered_images:
    #     ami_name = None
    #     for tag in image.tags:
    #         if tag['Key'] == 'Name':
    #             ami_name = tag['Value']
    #             break
    #     print("AMI Name:", ami_name)
    #     print(image.id)

    # print("Images",images)
    for i in images:
        # print("Image id:----------------------------",i.id)

        # tags = [{'Key': tag['Key'], 'Value': tag['Value']} for tag in i.tags]

        response = i.modify_attribute(
            Attribute='launchPermission',
            LaunchPermission={
                'Add': [
                    {
                        'UserId': target_account_id,
                    }
                ]
            },
            OperationType='add',
            # Tags=tags
        )
        print(response)

        # Retrieve the block device mappings for the AMI
        block_device_mappings = i.block_device_mappings
        # Modify volume permissions for each attached volume
        for mapping in block_device_mappings:
            if 'Ebs' in mapping:
                print("MappingngngngnL-----", mapping['Ebs'])
                snapshot_id = mapping['Ebs']['SnapshotId']
                client = session.client('ec2')
                response_snapshot = client.modify_snapshot_attribute(
                    SnapshotId=snapshot_id,
                    CreateVolumePermission={
                        'Add': [{'UserId': target_account_id}]
                    },
                    OperationType='add'
                )

                print("Snapshot ID:", snapshot_id)
                print("Snapshot Permission Response:", response_snapshot)
                # volume = boto3.resource('ec2').Volume(volume_id)
                # response_volume = volume.modify_attribute(
                #     Attribute='createVolumePermission',
                #     CreateVolumePermission={
                #         'Add': [{'UserId': target_account_id}]
                #     },
                #     OperationType='add'
                # )
                # print("Volume ID:", volume_id)
                # print("Volume Permission Response:", response_volume)

        print("AMI ID:", i.id)


    return images

def copy_ami(session, source_region, target_region, ami_id):
    """
    This function is used to copy the unencrypted AMI to encrypted AMI using KMS key in BU account.
    """

    for i in ami_id:
        tags = [{'Key': tag['Key'], 'Value': tag['Value']} for tag in i.tags]
        print("Mytags: -----",tags)
        client = session.client('ec2', region_name = target_region)

        filtered_tags = remove_aws_tags(tags)

        response = client.copy_image(
            Description='Encrypted Golden Image',
            Encrypted=True,
            # KmsKeyId='KmsKeyId/KmsKeyARN',
            Name='Demo-Copy-AMI',
            SourceImageId=i.id,
            SourceRegion=source_region,
            TagSpecifications=[{'ResourceType': 'image', 'Tags': filtered_tags}]
        )
        
        imId = response["ImageId"]
        
        # return None
        return response["ImageId"]


def main():
    #Get Main Session
    session = get_main_session()
    #Add Launch permission for AMI
    ami_id = add_launch_permission(session , source_region)
    #Get Temp Cred
    temp_cred = get_temp_cred(session, role_on_target_account, target_account_id)
    #Get Temp Session
    print(temp_cred)
    temp_session = get_temp_session(temp_cred, target_region)
    #Copy AMI
    print("Temp session")
    print(temp_session)
    image_id = copy_ami(temp_session, source_region, target_region, ami_id)
    print("Copied image id:- ",image_id)

if __name__ == '__main__':
    main()