import os, json
from bl.dict import Dict
from importlib import import_module

CONVERTERS_FILENAME = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'converters.json')

class Converter(Dict):
    """abstract base class for converters. Required interface:
    >>> source_obj = "This is a source"             # would usually be an instance of a content class
    >>> converter = Converter()                     # no initialization params required, but could be included
    >>> dest_obj = converter.convert(source_obj)    # returns dest_obj from the conversion of source_obj
    """
    def convert(self, source_obj, **params):
        pass

    @classmethod
    def find(Class, in_class, out_class, converters_filename=CONVERTERS_FILENAME):
        """returns a converter, if found, for the given combination of classes, using the converters.json config.
        in_class    : the class of the input object, either the class itself or a string representation of it.
        out_class   : the class of the output object, either the class itself or a string representation of it.
        """
        # make sure in_class and out_class are strings, because that is what we have in converters.json.
        if type(in_class)==type:
            in_class_str = '.'.join([in_class.__module__, in_class.__name__])
        else:
            in_class_str = in_class
        if type(out_class)==type:
            out_class_str = '.'.join([out_class.__module__, out_class.__name__])
        else:
            out_class_str = out_class
        
        # load converters.json 
        with open(converters_filename, 'r') as f:
            converters_list = json.load(f)

        # try to find the converter, return if found
        for converter in converters_list:
            if converter[0:2] == [in_class_str, out_class_str] and converter[2] is not None:
                mod_name = '.'.join(converter[2].split('.')[:-1])
                class_name = converter[2].split('.')[-1]
                mod = import_module(mod_name)
                return mod.__dict__.get(class_name)()
