import yaml

from cppwg.input.module_info import CppModuleInfo


class PackageInfoParser():

    def __init__(self, file_path, source_root):

        self.file_path = file_path
        self.raw_info = {}
        self.package_name = "cppwg_package"
        self.modules = []
        self.source_root = source_root

    def parse(self):

        with open(self.file_path, 'r') as myfile:
            data = myfile.read()

        self.raw_info = yaml.load(data)
        self.package_name = self.raw_info['name']

        for eachModule in self.raw_info['modules']:
            self.modules.append(CppModuleInfo(eachModule['name'],
                                              self.source_root,
                                              eachModule['source_locations'],
                                              eachModule['classes'],
                                              eachModule['free_functions']))
