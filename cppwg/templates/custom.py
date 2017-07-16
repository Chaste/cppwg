"""
This class returns custom code snippets for use during the wrapper
generation processes. It can be used as a base classs for
custom code generators.
"""

class Custom(object):
    
    def __init__(self):
        
        pass
    
    def get_class_cpp_pre_code(self, *args, **kwargs):
        
        return ""
    
    def get_class_cpp_def_code(self,  *args, **kwargs):
        
        return ""