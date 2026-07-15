# generated from rosidl_generator_py/resource/_idl.py.em
# with input from touch_glove_msgs:msg/TouchFrame.idl
# generated code does not contain a copyright notice


# Import statements for member types

import builtins  # noqa: E402, I100

import rosidl_parser.definition  # noqa: E402, I100


class Metaclass_TouchFrame(type):
    """Metaclass of message 'TouchFrame'."""

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
                'touch_glove_msgs.msg.TouchFrame')
            logger.debug(
                'Failed to import needed modules for type support:\n' +
                traceback.format_exc())
        else:
            cls._CREATE_ROS_MESSAGE = module.create_ros_message_msg__msg__touch_frame
            cls._CONVERT_FROM_PY = module.convert_from_py_msg__msg__touch_frame
            cls._CONVERT_TO_PY = module.convert_to_py_msg__msg__touch_frame
            cls._TYPE_SUPPORT = module.type_support_msg__msg__touch_frame
            cls._DESTROY_ROS_MESSAGE = module.destroy_ros_message_msg__msg__touch_frame

            from sensor_msgs.msg import Image
            if Image.__class__._TYPE_SUPPORT is None:
                Image.__class__.__import_type_support__()

            from std_msgs.msg import Header
            if Header.__class__._TYPE_SUPPORT is None:
                Header.__class__.__import_type_support__()

    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        # list constant names here so that they appear in the help text of
        # the message class under "Data and other attributes defined here:"
        # as well as populate each message instance
        return {
        }


class TouchFrame(metaclass=Metaclass_TouchFrame):
    """Message class 'TouchFrame'."""

    __slots__ = [
        '_header',
        '_channel',
        '_seq_id',
        '_timestamp_us',
        '_sensor_id',
        '_image',
    ]

    _fields_and_field_types = {
        'header': 'std_msgs/Header',
        'channel': 'uint8',
        'seq_id': 'uint32',
        'timestamp_us': 'uint64',
        'sensor_id': 'string',
        'image': 'sensor_msgs/Image',
    }

    SLOT_TYPES = (
        rosidl_parser.definition.NamespacedType(['std_msgs', 'msg'], 'Header'),  # noqa: E501
        rosidl_parser.definition.BasicType('uint8'),  # noqa: E501
        rosidl_parser.definition.BasicType('uint32'),  # noqa: E501
        rosidl_parser.definition.BasicType('uint64'),  # noqa: E501
        rosidl_parser.definition.UnboundedString(),  # noqa: E501
        rosidl_parser.definition.NamespacedType(['sensor_msgs', 'msg'], 'Image'),  # noqa: E501
    )

    def __init__(self, **kwargs):
        assert all('_' + key in self.__slots__ for key in kwargs.keys()), \
            'Invalid arguments passed to constructor: %s' % \
            ', '.join(sorted(k for k in kwargs.keys() if '_' + k not in self.__slots__))
        from std_msgs.msg import Header
        self.header = kwargs.get('header', Header())
        self.channel = kwargs.get('channel', int())
        self.seq_id = kwargs.get('seq_id', int())
        self.timestamp_us = kwargs.get('timestamp_us', int())
        self.sensor_id = kwargs.get('sensor_id', str())
        from sensor_msgs.msg import Image
        self.image = kwargs.get('image', Image())

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
        if self.channel != other.channel:
            return False
        if self.seq_id != other.seq_id:
            return False
        if self.timestamp_us != other.timestamp_us:
            return False
        if self.sensor_id != other.sensor_id:
            return False
        if self.image != other.image:
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
    def channel(self):
        """Message field 'channel'."""
        return self._channel

    @channel.setter
    def channel(self, value):
        if __debug__:
            assert \
                isinstance(value, int), \
                "The 'channel' field must be of type 'int'"
            assert value >= 0 and value < 256, \
                "The 'channel' field must be an unsigned integer in [0, 255]"
        self._channel = value

    @builtins.property
    def seq_id(self):
        """Message field 'seq_id'."""
        return self._seq_id

    @seq_id.setter
    def seq_id(self, value):
        if __debug__:
            assert \
                isinstance(value, int), \
                "The 'seq_id' field must be of type 'int'"
            assert value >= 0 and value < 4294967296, \
                "The 'seq_id' field must be an unsigned integer in [0, 4294967295]"
        self._seq_id = value

    @builtins.property
    def timestamp_us(self):
        """Message field 'timestamp_us'."""
        return self._timestamp_us

    @timestamp_us.setter
    def timestamp_us(self, value):
        if __debug__:
            assert \
                isinstance(value, int), \
                "The 'timestamp_us' field must be of type 'int'"
            assert value >= 0 and value < 18446744073709551616, \
                "The 'timestamp_us' field must be an unsigned integer in [0, 18446744073709551615]"
        self._timestamp_us = value

    @builtins.property
    def sensor_id(self):
        """Message field 'sensor_id'."""
        return self._sensor_id

    @sensor_id.setter
    def sensor_id(self, value):
        if __debug__:
            assert \
                isinstance(value, str), \
                "The 'sensor_id' field must be of type 'str'"
        self._sensor_id = value

    @builtins.property
    def image(self):
        """Message field 'image'."""
        return self._image

    @image.setter
    def image(self, value):
        if __debug__:
            from sensor_msgs.msg import Image
            assert \
                isinstance(value, Image), \
                "The 'image' field must be a sub message of type 'Image'"
        self._image = value
