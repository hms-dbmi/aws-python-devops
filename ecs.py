def create_ecs_cluster(ecs_client, cluster_name):
    print("Create ECS Cluster")
    ecs_client.create_cluster(clusterName=cluster_name)

def create_ecs_ec2(stack_name, cluster_name, vpc, ec2, userdata_string, settings, environment):

    print("Create EC2 for ECS")

    machine_tags = [{"Key": "owner", "Value": settings["MACHINE_OWNER"]},
                    {"Key": "environment", "Value": environment},
                    {"Key": "project", "Value": stack_name},
                    {"Key": "department", "Value": settings["GROUP_OWNER"]},
                    {"Key": "Name", "Value": cluster_name}]

    ec2_security_groups = list(vpc.security_groups.filter(Filters=[{'Name': 'tag:Name', 'Values': [stack_name + '_SG']}]))[0]

    new_instance = ec2.create_instances(ImageId=settings['AMI_IMAGE_ID'],
                                        MinCount=1,
                                        MaxCount=1,
                                        InstanceType=settings['EC2_INSTANCE_TYPE'],
                                        SecurityGroupIds=[ec2_security_groups.id],
                                        KeyName=settings['EC2_KEY_NAME'],
                                        UserData=userdata_string,
                                        IamInstanceProfile={"Arn": settings['EC2_IAM_INSTANCE_PROFILE_ARN']},
                                        Placement={'AvailabilityZone': settings['AVAILABILITY_ZONE']})

    new_instance[0].create_tags(Tags=machine_tags)
    new_instance[0].wait_until_running()


def create_ecs_task(ecs_client, task_family, cluster_name, settings, environment, taskname):

    print("Create ECS Task " + environment + " " + taskname)

    vault_path = settings["VAULT_PROJECT_NAME"] + '/' + taskname.lower() + "/" + environment + "/"
    db_vault_path = ""

    try:
        if settings["DB_VAULT_PROJECT_NAME"]:
            db_vault_path = settings["DB_VAULT_PROJECT_NAME"] + "/" + environment + "/"
    except KeyError:
        pass

    app_image_enviro_repo = settings["APP_IMAGE_REPO_" + taskname + "_" + environment.upper()]

    container_definition = [{
        'name': cluster_name + "_" + taskname,
        'image': app_image_enviro_repo,
        'memoryReservation': int(settings["CONTAINER_MEMORY_RESERVATION"]),
        'memory': int(settings["CONTAINER_MEMORY"]),
        'portMappings': [
            {'hostPort': int(settings[taskname + "_PORT"]), 'containerPort': int(settings[taskname + "_PORT"])}],
        'environment': [{'name': 'VAULT_ADDR', 'value': settings["VAULT_URL"]},
                        {'name': 'VAULT_PATH', 'value': vault_path},
                        {'name': 'DB_VAULT_PATH', 'value': db_vault_path},
                        {'name': 'VAULT_SKIP_VERIFY', 'value': '1'}]
    }]

    try:
        if settings["INCLUDE_ECS_CLOUDWATCH"] == "True":
            container_definition[0]["logConfiguration"] = {
                "logDriver": "awslogs",
                "options": {
                    "awslogs-group": settings["CLOUDWATCH_GROUP"] + environment,
                    "awslogs-region": "us-east-1",
                    "awslogs-stream-prefix": settings["CLOUDWATCH_PREFIX"]
                }
            }
    except KeyError:
        pass

    ecs_client.register_task_definition(family=task_family + "-" + taskname, containerDefinitions=container_definition)



















