-- ============================================================================

-- 大小模型协同训练模块菜单初始化脚本

-- ============================================================================

-- 说明：将大小模型协同训练页面添加到系统菜单，使其在动态路由模式下可访问

-- 执行方式：mysql -u root -pqczy1717 datamark < add_model_distillation_menu.sql

-- ============================================================================

USE mark;


-- 1. 插入大小模型协同训练菜单（一级菜单）

INSERT INTO `qczy_menu` (

    `id`,

    `parent_id`,

    `menu_name`,

    `icon`,

    `local_icon`,

    `permissions`,

    `i18nKey`,

    `web_path`,

    `component`,

    `active_menu`,

    `type`,

    `sort`,

    `create_time`,

    `update_time`,

    `hide_in_menu`,

    `is_deleted`,

    `href`

) VALUES (

             67,                                    -- 菜单ID（确保不与现有菜单冲突）

             0,                                     -- 父菜单ID（0 表示顶级菜单）

             'model-distillation',                  -- 菜单名称（与前端路由对应）

             'carbon:model',                        -- 图标

             'carbon:model',                        -- 本地图标

             NULL,                                  -- 权限标识

             'route.model-distillation',           -- 国际化Key

             '/model-distillation',                 -- URL路径

             'layout.base$view.model-distillation', -- Vue组件路径

             NULL,                                  -- 激活菜单

             1,                                     -- 类型（1=菜单）

             9,                                     -- 排序（在联邦学习之后）

             NOW(),                                 -- 创建时间

             NOW(),                                 -- 更新时间

             0,                                     -- 是否隐藏（0=显示）

             0,                                     -- 是否删除（0=未删除）

             NULL                                   -- 外链

         );



-- 2. 将菜单分配给管理员角色（role_id = 1）

INSERT INTO `qczy_role_menu` (`role_id`, `menu_id`) VALUES (1, 67);


-- ============================================================================

-- 执行完成后，请执行以下操作：

-- 1. 退出登录

-- 2. 重新使用 admin 账户登录

-- 3. 在左侧菜单栏应该能看到 "大小模型协同训练" 菜单

-- 4. 点击菜单或访问 http://localhost:8080/#/model-distillation

-- ============================================================================