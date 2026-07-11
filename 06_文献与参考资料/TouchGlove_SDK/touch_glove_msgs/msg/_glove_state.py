# generated from rosidl_generator_py/resource/_idl.py.em
# with input from touch_glove_msgs:msg/GloveState.idl
# generated code does not contain a copyright notice


# Import statements for member types

import builtins  # noqa: E402, I100

import rosidl_parser.definition  # noqa: E402, I100


class Metaclass_GloveState(type):
    """Metaclass of message 'GloveState'."""

    _CREATE_ROS_MESSAGE = None
    _CONVERT_FROM_PY = None
    _CONVERT_TO_PY = None
    _DESTROY_ROS_MESSAGE = None
    _TYPE_SUPPORT = None

    __constants = {
    }

    @classmethod
    def __import_type_support__(cls):
        try:
            from rosidl_generator_py import import_type_support
            module = import_type_support('touch_glove_msgs')
        except ImportError:
            import logging
            import traceback
            logger = logging.getLogger(
                'touch_glove_msgs.msg.GloveState')
            logger.debug(
                'Failed to import needed modules for type support:\n' +
                traceback.format_exc())
        else:
            cls._CREATE_ROS_MESSAGE = module.create_ros_message_msg__msg__glove_state
            cls._CONVERT_FROM_PY = module.convert_from_py_msg__msg__glove_state
            cls._CONVERT_TO_PY = module.convert_to_py_msg__msg__glove_state
            cls._TYPE_SUPPORT = module.type_support_msg__msg__glove_state
            cls._DESTROY_ROS_MESSAGE = module.destroy_ros_message_msg__msg__glove_state

            from std_msgs.msg import Header
            if Header.__class__._TYPE_SUPPORT is None:
                Header.__class__.__import_type_support__()

            from touch_glove_msgs.msg import FingerData
            if FingerData.__class__._TYPE_SUPPORT is None:
                FingerData.__class__.__import_type_support__()

    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        # list constant names here so that they appear in the help text of
        # the message class under "Data and other attributes defined here:"
        # as well as populate each message instance
        return {
        }


class GloveState(metaclass=Metaclass_GloveState):
    """Message class 'GloveState'."""

    __slots__ = [
        '_header',
        '_ch1',
        '_ch2',
        '_ch3',
        '_ch4',
        '_ch5',
    ]

    _fields_and_field_types = {
        'header': 'std_msgs/Header',
        'ch1': 'touch_glove_msgs/FingerData',
        'ch2': 'touch_glove_msgs/FingerData',
        'ch3': 'touch_glove_msgs/FingerData',
        'ch4': 'touch_glove_msgs/FingerData',
        'ch5': 'touch_glove_msgs/FingerData',
    }

    SLOT_TYPES = (
        rosidl_parser.definition.NamespacedType(['std_msgs', 'msg'], 'Header'),  # noqa: E501
        rosidl_parser.definition.NamespacedType(['touch_glove_msgs', 'msg'], 'FingerData'),  # noqa: E501
        rosidl_parser.definition.NamespacedType(['touch_glove_msgs', 'msg'], 'FingerData'),  # noqa: E501
        rosidl_parser.definition.NamespacedType(['touch_glove_msgs', 'msg'], 'FingerData'),  # noqa: E501
        rosidl_parser.definition.NamespacedType(['touch_glove_msgs', 'msg'], 'FingerData'),  # noqa: E501
        rosidl_parser.definition.NamespacedType(['touch_glove_msgs', 'msg'], 'FingerData'),  # noqa: E501
    )

    def __init__(self, **kwargs):
        assert all('_' + key in self.__slots__ for key in kwargs.keys()), \
            'Invalid arguments passed to constructor: %s' % \
            ', '.join(sorted(k for k in kwargs.keys() if '_' + k not in self.__slots__))
        from std_msgs.msg import Header
        self.header = kwargs.get('header', Header())
        from touch_glove_msgs.msg import FingerData
        self.ch1 = kwargs.get('ch1', FingerData())
        from touch_glove_msgs.msg import FingerData
        self.ch2 = kwargs.get('ch2', FingerData())
        from touch_glove_msgs.msg import FingerData
        self.ch3 = kwargs.get('ch3', FingerData())
        from touch_glove_msgs.msg import FingerData
        self.ch4 = kwargs.get('ch4', FingerData())
        from touch_glove_msgs.msg import FingerData
        self.ch5 = kwargs.get('ch5', FingerData())

    def __repr__(self):
        typename = self.__class__.__module__.split('.')
        typename.pop()
        typename.append(self.__class__.__name__)
        args = []
        for s, t in zip(self.__slots__, self.SLOT_TYPES):
            field = getattr(self, s)
            fieldstr = repr(field)
            # We use Python array type for fields that can be directly stored
            # in them, and "normal" sequences for everything else.  If it is
            # a type that we store in an array, strip off the 'array' portion.
            if (
                isinstance(t, rosidl_parser.definition.AbstractSequence) and
                isinstance(t.value_type, rosidl_parser.definition.BasicType) and
                t.value_type.typename in ['float', 'double', 'int8', 'uint8', 'int16', 'uint16', 'int32', 'uint32', 'int64', 'uint64']
            ):
                if len(field) == 0:
                    fieldstr = '[]'
                else:
                    assert fieldstr.startswith('array(')
                    prefix = "array('X', "
                    suffix = ')'
                    fieldstr = fieldstr[len(prefix):-len(suffix)]
            args.append(s[1:] + '=' + fieldstr)
        return '%s(%s)' % ('.'.join(typename), ', '.join(args))

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        if self.header != other.header:
            return False
        if self.ch1 != other.ch1:
            return False
        if self.ch2 != other.ch2:
            return False
        if self.ch3 != other.ch3:
            return False
        if self.ch4 != other.ch4:
            return False
        if self.ch5 != other.ch5:
            return False
        return True

    @classmethod
    def get_fields_and_field_types(cls):
        from copy import copy
        return copy(cls._fields_and_field_types)

    @builtins.property
    def header(self):
        """Message field 'header'."""
        return self._header

    @header.setter
    def header(self, value):
        if __debug__:
            from std_msgs.msg import Header
            assert \
                isinstance(value, Header), \
                "The 'header' field must be a sub message of type 'Header'"
        self._header = value

    @builtins.property
    def ch1(self):
        """Message field 'ch1'."""
        return self._ch1

    @ch1.setter
    def ch1(self, value):
        if __debug__:
            from touch_glove_msgs.msg import FingerData
            assert \
                isinstance(value, FingerData), \
                "The 'ch1' field must be a sub message of type 'FingerData'"
        self._ch1 = value

    @builtins.property
    def ch2(self):
        """Message field 'ch2'."""
        return self._ch2

    @ch2.setter
    def ch2(self, value):
        if __debug__:
            from touch_glove_msgs.msg import FingerData
            assert \
                isinstance(value, FingerData), \
                "The 'ch2' field must be a sub message of type 'FingerData'"
        self._ch2 = value

    @builtins.property
    def ch3(self):
        """Message field 'ch3'."""
        return self._ch3

    @ch3.setter
    def ch3(self, value):
        if __debug__:
            from touch_glove_msgs.msg import FingerData
            assert \
                isinstance(value, FingerData), \
                "The 'ch3' field must be a sub message of type 'FingerData'"
        self._ch3 = value

    @builtins.property
    def ch4(self):
        """Message field 'ch4'."""
        return self._ch4

    @ch4.setter
    def ch4(self, value):
        if __debug__:
            from touch_glove_msgs.msg import FingerData
            assert \
                isinstance(value, FingerData), \
                "The 'ch4' field must be a sub message of type 'FingerData'"
        self._ch4 = value

    @builtins.property
    def ch5(self):
        """Message field 'ch5'."""
        return self._ch5

    @ch5.setter
    def ch5(self, value):
        if __debug__:
            from touch_glove_msgs.msg import FingerData
            assert \
                isinstance(value, FingerData), \
                "The 'ch5' field must be a sub message of type 'FingerData'"
        self._ch5 = value
