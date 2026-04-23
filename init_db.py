from app import create_app
from app.extensions import db, bcrypt
from app.models.auth.user import User
from app.models.system.factory import Factory
from app.models.system.user_factory import UserFactory
from app.models.system.user_factory_role import UserFactoryRole
from app.models.system.role import Role
from datetime import datetime

app = create_app()

with app.app_context():
    # 创建所有表
    db.create_all()
    print('✅ 数据库表创建成功')

    # ========== 创建管理员 ==========
    admin = User.query.filter_by(username='admin', is_deleted=0).first()
    if not admin:
        admin = User(
            username='admin',
            password=bcrypt.generate_password_hash('123456').decode('utf-8'),
            nickname='超级管理员',
            is_admin=1,
            status=1
        )
        admin.save()
        print('✅ 管理员创建成功 - 用户名: admin, 密码: 123456')
    else:
        print('⚠️ 管理员已存在')

    # ========== 创建测试工厂 ==========
    factory = Factory.query.filter_by(code='TEST001', is_deleted=0).first()
    if not factory:
        factory = Factory(
            name='测试工厂',
            code='TEST001',
            contact_person='张三',
            contact_phone='13800138000',
            address='广东省深圳市南山区',
            status=1
        )
        factory.save()
        print(f'✅ 测试工厂创建成功 - {factory.name}')

        # ========== 创建工厂管理员（员工） ==========
        factory_admin = User.query.filter_by(username='factory_admin', is_deleted=0).first()
        if not factory_admin:
            factory_admin = User(
                username='factory_admin',
                password=bcrypt.generate_password_hash('123456').decode('utf-8'),
                nickname='工厂管理员',
                is_admin=0,
                status=1
            )
            factory_admin.save()

            # 关联用户到工厂（作为员工）
            user_factory = UserFactory(
                user_id=factory_admin.id,
                factory_id=factory.id,
                relation_type='employee',
                status=1,
                entry_date=datetime.now().date()
            )
            user_factory.save()
            print('✅ 工厂管理员创建成功 - 用户名: factory_admin, 密码: 123456')

        # ========== 创建工厂员工 ==========
        employee = User.query.filter_by(username='factory_employee', is_deleted=0).first()
        if not employee:
            employee = User(
                username='factory_employee',
                password=bcrypt.generate_password_hash('123456').decode('utf-8'),
                nickname='工厂员工',
                is_admin=0,
                status=1
            )
            employee.save()

            # 关联用户到工厂（作为员工）
            user_factory = UserFactory(
                user_id=employee.id,
                factory_id=factory.id,
                relation_type='employee',
                status=1,
                entry_date=datetime.now().date()
            )
            user_factory.save()
            print('✅ 工厂员工创建成功 - 用户名: factory_employee, 密码: 123456')

        # ========== 创建工厂客户 ==========
        customer = User.query.filter_by(username='factory_customer', is_deleted=0).first()
        if not customer:
            customer = User(
                username='factory_customer',
                password=bcrypt.generate_password_hash('123456').decode('utf-8'),
                nickname='工厂客户',
                is_admin=0,
                status=1
            )
            customer.save()

            # 关联用户到工厂（作为客户）
            user_factory = UserFactory(
                user_id=customer.id,
                factory_id=factory.id,
                relation_type='customer',
                status=1,
                entry_date=datetime.now().date()
            )
            user_factory.save()
            print('✅ 工厂客户创建成功 - 用户名: factory_customer, 密码: 123456')

        # ========== 创建工厂协作用户 ==========
        collaborator = User.query.filter_by(username='factory_collaborator', is_deleted=0).first()
        if not collaborator:
            collaborator = User(
                username='factory_collaborator',
                password=bcrypt.generate_password_hash('123456').decode('utf-8'),
                nickname='工厂协作用户',
                is_admin=0,
                status=1
            )
            collaborator.save()

            # 关联用户到工厂（作为协作用户）
            user_factory = UserFactory(
                user_id=collaborator.id,
                factory_id=factory.id,
                relation_type='collaborator',
                status=1,
                entry_date=datetime.now().date()
            )
            user_factory.save()
            print('✅ 工厂协作用户创建成功 - 用户名: factory_collaborator, 密码: 123456')

        # ========== 创建角色 ==========
        # 创建管理员角色
        admin_role = Role.query.filter_by(factory_id=factory.id, code='admin', is_deleted=0).first()
        if not admin_role:
            admin_role = Role(
                factory_id=factory.id,
                name='管理员',
                code='admin',
                description='工厂管理员，拥有所有权限',
                status=1,
                sort_order=1
            )
            admin_role.save()
            print('✅ 管理员角色创建成功')

            # 分配角色给工厂管理员
            ufr = UserFactoryRole(
                user_id=factory_admin.id,
                factory_id=factory.id,
                role_id=admin_role.id
            )
            ufr.save()
            print('✅ 已分配管理员角色给工厂管理员')

        # 创建员工角色
        staff_role = Role.query.filter_by(factory_id=factory.id, code='staff', is_deleted=0).first()
        if not staff_role:
            staff_role = Role(
                factory_id=factory.id,
                name='员工',
                code='staff',
                description='普通员工权限',
                status=1,
                sort_order=2
            )
            staff_role.save()
            print('✅ 员工角色创建成功')

            # 分配角色给工厂员工
            ufr = UserFactoryRole(
                user_id=employee.id,
                factory_id=factory.id,
                role_id=staff_role.id
            )
            ufr.save()
            print('✅ 已分配员工角色给工厂员工')

    else:
        print('⚠️ 测试工厂已存在')

    print('🎉 初始化完成！')

    # 打印账号汇总
    print('\n========== 账号汇总 ==========')
    print('平台账号：')
    print('  - 用户名: admin, 密码: 123456 (超级管理员)')
    print('\n工厂账号：')
    print('  - 用户名: factory_admin, 密码: 123456 (工厂管理员)')
    print('  - 用户名: factory_employee, 密码: 123456 (工厂员工)')
    print('  - 用户名: factory_customer, 密码: 123456 (工厂客户)')
    print('  - 用户名: factory_collaborator, 密码: 123456 (工厂协作用户)')
    print('===============================')
