import sys, os, yaml, time, shutil, pprint
import boto3, botocore
from botocore.exceptions import ClientError

class AWS_UTIL:

    columns, lines = shutil.get_terminal_size((80, 20)) # get the terminal sizing for some printouts later

    def __init__(self, aws_access_key, aws_secret_access_key):
        self.aws_access_key = aws_access_key
        self.aws_secret_access_key = aws_secret_access_key
        self.available_regions = ['us-east-1', 
                                   'us-east-2', 
                                   'us-west-1', 
                                   'us-west-2', 
                                   'ap-south-1', 
                                   'ap-northeast-2', 
                                   'ap-southeast-1',
                                   'ap-southeast-2',
                                   'ca-central-1',
                                   'eu-central-1',
                                   'eu-west-1',
                                   'eu-west-2',
                                   'eu-west-3',
                                   'eu-north-1',
                                   'sa-east-1']
        self.set_region(self.available_regions[0])


    def set_region(self, region):
        """
        Function to regerate all of the AWS clients to target a different AWS Region.  
        """
        if region in self.available_regions:
            self.session = boto3.Session(aws_access_key_id=self.aws_access_key, aws_secret_access_key=self.aws_secret_access_key, region_name=region)
            self.lambda_client = self.session.client('lambda')
            self.ecs_client = self.session.client('ecs')
            # self.ec2_client = self.session.client('ec2')
            # self.elb_client = self.session.client('elb')
            # self.elb2_client = self.session.client('elbv2')
            # self.s3_client = self.session.client('s3')
            # self.route53_client = self.session.client('route53')
            # self.iam_client = self.session.client('iam')


    def get_unpaginated_query_results(self, query_method, data_key, validation_key=None, validation_value=None, strict_validation=True, filters=None, marker_key="NextMarker", marker_name="Marker"):
        """
        Get the results from a query using query_method, and unpaginate them (put all pages of a result into one list)
        @params:
            query_method - the method/function to call to complete the query from the AWS boto3 clients api
            data_key - a key used to access the data element of the query response
            validation_key (optional) - a key to use to access each response data element's validation parameter (the field of the response on which you want to filter)
            validation_value (optional) - a value to filter response[data_key][validation_key] against.  
            filters (optional) - filters to specify within the call to query_method
        """
        dataset = []
        data = query_method() if filters is None else query_method(Filters=filters) # Base Query w/ filter option
        next_marker = ""
        while next_marker is not None:

            # Process data
            if validation_key is not None and validation_value is not None:
                # If we're asked to validate against a key (typically when a filter is not provided and we have to filter)
                for d in data[data_key]:
                    # Loop through all the entries, if validated agains validation_value, push to list
                    if strict_validation and d[validation_key] == validation_value:
                        dataset.append(d)
                    elif not strict_validation and validation_value in d[validation_key]:
                        dataset.append(d)
            else:
                # If we don't have to validate against a key, just append the whole list
                dataset = dataset + data[data_key] if data_key in data else dataset

            # Setup for next iteration/page or end if no more pages
            if marker_key in data:
                # If the query returned a 'NextMarker' there is a next page
                if marker_name == "Marker":
                    next_marker = data[marker_key]
                    data = query_method(Marker=next_marker) if filters is None else query_method(Filters=filters, Marker=next_marker) # Base Query w/ filter option
                elif marker_name == "NextToken":
                    next_marker = data[marker_key]
                    data = query_method(NextToken=next_marker) if filters is None else query_method(Filters=filters, NextToken=next_marker) # Base Query w/ filter option
                else:
                    print("Invalid next_marker configuration, returning an empty list.")
                    return []
            else:
                # Otherwise, we're done
                next_marker = None 
        return dataset

    
    '''## LAMBDA RESOURCES'''
    def list_lambda_resources(self):
        pp = pprint.PrettyPrinter()
        _found_count = 0
        for region in self.available_regions:
            self.set_region(region)
            _functions = self.list_functions()
            _aliases = self.list_aliases(_functions)
            _source_mappings = self.list_event_source_mappings()
            _invoke_configs = self.list_function_event_invoke_configs(_functions)
            _versions = self.list_versions_by_function(_functions)
            _layers = self.list_layers()
            _layer_versions = self.list_layer_versions(_layers)
            _provisioned_concurrency_configs = self.list_provisioned_concurrency_configs(_functions)
            _found_count = _found_count + len(_functions) + len(_aliases) + len(_source_mappings) + len(_invoke_configs)
            + len(_versions) + len(_layers) + len(_layer_versions) + len(_provisioned_concurrency_configs)
            print(f"## Resources in {region}")
            print("### Functions")
            pp.pprint(_functions)
            print("### Aliases")
            pp.pprint(_aliases)
            print("### Event Source Mappings")
            pp.pprint(_source_mappings)
            print("### Function Event Invoke Configs")
            pp.pprint(_invoke_configs)
            print("### Versions")
            pp.pprint(_versions)
            print("### Layers")
            pp.pprint(_layers)
            print("### Layer Versions")
            pp.pprint(_layer_versions)
            print("### Provisioned Concurrency Configs")
            pp.pprint(_provisioned_concurrency_configs)
        print (f"## {_found_count} Resources Found Across All Regions")


    def list_aliases(self, functions):
        _aliases = []
        for _function in functions:
            _local_aliases = self.lambda_client.list_aliases(FunctionName=_function["FunctionName"])["Aliases"]
            if len(_local_aliases) > 0:
                _aliases.append({"FuncitonName": _function["FunctionName"], "aliases": _local_aliases})
        return _aliases


    def list_functions(self):
        return self.lambda_client.list_functions()['Functions']

    
    def list_event_source_mappings(self):
        return self.lambda_client.list_event_source_mappings()['EventSourceMappings']

    
    def list_function_event_invoke_configs(self, functions):
        _function_event_invoke_configs = []
        for _function in functions:
            _local_feic = self.lambda_client.list_function_event_invoke_configs(FunctionName=_function["FunctionName"])['FunctionEventInvokeConfigs']
            if len(_local_feic) > 0:
                _function_event_invoke_configs.append({"FunctionName": _function["FunctionName"], 
                    "function_event_invoke_configs": _local_feic})
        return _function_event_invoke_configs


    def list_layer_versions(self, layers):
        _layer_versions = []
        for _layer in layers:
            _local_lv = self.lambda_client.list_layer_versions(FunctionName=_layer["LayerName"])['LayerVersion']
            if len(_local_lv) > 0:
                _layer_versions.append({"FunctionName": _function["FunctionName"], 
                    "LayerVersions": _local_lv})
        return _layer_versions


    def list_layers(self):
        return self.lambda_client.list_layers()["Layers"]


    def list_versions_by_function(self, functions):
        _versions = []
        for _function in functions:
            _local_v = self.lambda_client.list_versions_by_function(FunctionName=_function["FunctionName"])['Versions']
            if len(_local_v) > 0:
                _versions.append({"FunctionName": _function["FunctionName"], 
                    "Versions": _local_v})
        return _versions


    def list_provisioned_concurrency_configs(self, functions):
        _provisioned_concurrency_configs = []
        for _function in functions:
            _local_pcc = self.lambda_client.list_provisioned_concurrency_configs(FunctionName=_function["FunctionName"])['ProvisionedConcurrencyConfigs']
            if len(_local_pcc) > 0:
                _provisioned_concurrency_configs.append({"FunctionName": _function["FunctionName"], 
                    "ProvisinedConcurrencyConfigs": _local_pcc})
        return _provisioned_concurrency_configs


    '''## FARGATE/ECS RESOURCES'''
    def list_fargate_resources(self):
        pp = pprint.PrettyPrinter()
        _found_count = 0
        for region in self.available_regions:
            self.set_region(region)
            _clusters = self.list_clusters()
            _attributes = self.list_attributes(_clusters)
            _container_instances = self.list_container_instances(_clusters)
            _services = self.list_services(_clusters)
            _tasks = self.list_tasks(_clusters)
            _found_count = _found_count + len(_clusters) + len(_attributes) + len(_container_instances)
            + len(_services) + len(_tasks)
            print(f"## Resources in {region}")
            print("### Clusters")
            pp.pprint(_clusters)
            print("### Attributes")
            pp.pprint(_attributes)
            print("### Container Instances")
            pp.pprint(_container_instances)
            print("### Services")
            pp.pprint(_services)
            print("### Tasks")
            pp.pprint(_tasks)
        print (f"## {_found_count} Resources Found Across All Regions")


    def list_attributes(self, clusters):
        _attributes = []
        for _cluster in clusters:
            _local_a = self.ecs_client.list_attributes(targetType="container-instance", cluster=_cluster)
            if 'nextToken' in _local_a:
                print(f"Cluster: {_cluster} contained too many attributes for one API call, manual validation required!".ljust(AWS_UTIL.columns, "<"))
            if len(_local_a['attributes']) > 0:
                _attributes.append({"clusterARN": _cluster, 
                    "Attributes": _local_a['attributes']})
        return _attributes


    def list_clusters(self):
        return self.get_unpaginated_query_results(self.ecs_client.list_clusters, "clusterArns", marker_key="NextToken")

    
    def list_container_instances(self, clusters):
        _container_instances = []
        for _cluster in clusters:
            _local_ci = self.ecs_client.list_container_instances(cluster=_cluster)
            if 'nextToken' in _local_ci:
                print(f"Cluster: {_cluster} contained too many container instances for one API call, manual validation required!".ljust(AWS_UTIL.columns, "<"))
            if len(_local_ci['containerInstanceArns']) > 0:
                _container_instances.append({"clusterARN": _cluster, 
                    "ContainerInstances": _local_ci['containerInstanceArns']})
        return _container_instances


    def list_services(self, clusters):
        _services = []
        for _cluster in clusters:
            for _launch_type in ["FARGATE", "EC2"]:
                _local_svc = self.ecs_client.list_services(cluster=_cluster, launchType=_launch_type)
                if 'nextToken' in _local_svc:
                    print(f"Cluster: {_cluster} contained too many {_launch_type} services for one API call, manual validation required!".ljust(AWS_UTIL.columns, "<"))
                if len(_local_svc['serviceArns']) > 0:
                    _services.append({"clusterARN": _cluster, 
                        "Services": _local_ci['serviceArns']})
        return _services


    def list_tasks(self, clusters):
        _tasks = []
        for _cluster in clusters:
            for _launch_type in ["FARGATE", "EC2"]:
                _local_tasks = self.ecs_client.list_tasks(cluster=_cluster, launchType=_launch_type)
                if 'nextToken' in _local_tasks:
                    print(f"Cluster: {_cluster} contained too many {_launch_type} tasks for one API call, manual validation required!".ljust(AWS_UTIL.columns, "<"))
                if len(_local_tasks['taskArns']) > 0:
                    _tasks.append({"clusterARN": _cluster, 
                        "Tasks": _local_ci['taskArns']})
        return _tasks


if __name__ == "__main__":
    aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')

    util = AWS_UTIL(aws_access_key=aws_access_key, aws_secret_access_key=aws_secret_access_key)
    print(f"# LAMBDA RESOURCES")
    util.list_lambda_resources()
    print(f"# FARGATE/ECS RESOURCES")
    util.list_fargate_resources()
