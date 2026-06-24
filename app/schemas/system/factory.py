"""工厂相关序列化定义。"""

from marshmallow import Schema, fields, validate


FACTORY_RELATION_TYPE_CHOICES = ['owner', 'employee', 'collaborator']
FACTORY_COLLABORATOR_TYPE_CHOICES = ['button_partner', 'shrink_partner', 'print_partner', 'other_partner']
FACTORY_SUBJECT_CATEGORY_CHOICES = ['factory', 'button_shop', 'shrink_factory', 'print_factory', 'other']


class FactorySchema(Schema):
    """工厂返回结构。"""

    id = fields.Int()
    name = fields.Str()
    code = fields.Str()
    subject_id = fields.Int()
    subject_category = fields.Str()
    subject_label = fields.Str()
    contact_person = fields.Str()
    contact_phone = fields.Str()
    address = fields.Str()
    status = fields.Int()
    remark = fields.Str()
    service_expire_date = fields.Date(format="%Y-%m-%d", allow_none=True)
    service_status = fields.Str()
    create_time = fields.DateTime(format="%Y-%m-%d %H:%M:%S")
    update_time = fields.DateTime(format="%Y-%m-%d %H:%M:%S")


class FactoryCreateSchema(Schema):
    """创建工厂入参，工厂编码由系统自动生成。"""

    name = fields.Str(required=True, validate=validate.Length(min=2, max=100))
    subject_category = fields.Str(validate=validate.OneOf(FACTORY_SUBJECT_CATEGORY_CHOICES))
    subject_label = fields.Str(validate=validate.Length(max=50))
    contact_person = fields.Str(validate=validate.Length(max=50))
    contact_phone = fields.Str(validate=validate.Length(max=20))
    address = fields.Str(validate=validate.Length(max=255))
    service_expire_date = fields.Date(format="%Y-%m-%d", allow_none=True)
    remark = fields.Str(validate=validate.Length(max=500))


class FactoryUpdateSchema(Schema):
    """更新工厂入参。"""

    name = fields.Str(validate=validate.Length(min=2, max=100))
    subject_category = fields.Str(validate=validate.OneOf(FACTORY_SUBJECT_CATEGORY_CHOICES))
    subject_label = fields.Str(validate=validate.Length(max=50))
    contact_person = fields.Str(validate=validate.Length(max=50))
    contact_phone = fields.Str(validate=validate.Length(max=20))
    address = fields.Str(validate=validate.Length(max=255))
    service_expire_date = fields.Date(format="%Y-%m-%d", allow_none=True)
    status = fields.Int(validate=validate.OneOf([0, 1]))
    remark = fields.Str(validate=validate.Length(max=500))


class FactoryAddUserSchema(Schema):
    """工厂新增关联用户入参。"""

    user_id = fields.Int(required=True, validate=validate.Range(min=1))
    relation_type = fields.Str(required=True, validate=validate.OneOf(FACTORY_RELATION_TYPE_CHOICES))
    collaborator_type = fields.Str(validate=validate.OneOf(FACTORY_COLLABORATOR_TYPE_CHOICES))


class FactoryBindSchema(Schema):
    """扫码绑定工厂入参。"""

    key = fields.Str(required=True, validate=validate.Length(min=1, max=100))
