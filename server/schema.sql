-- 钓鱼脚本卡密表
-- 用于存储卡密信息、激活状态、设备绑定和时效

CREATE TABLE `card_info` (
  `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
  `card_code` VARCHAR(32) NOT NULL UNIQUE COMMENT '卡密字符串（唯一）',
  `card_type` VARCHAR(16) NOT NULL COMMENT '卡密类型：2h/1d/7d/15d/30d/90d/365d',
  `valid_seconds` INT NOT NULL COMMENT '有效时长（秒）：2h=7200，1d=86400，7d=604800，15d=1296000，30d=2592000，90d=7776000，365d=31536000',
  `is_activated` TINYINT(1) DEFAULT 0 COMMENT '是否激活：0=未激活，1=已激活',
  `bind_device_code` VARCHAR(64) DEFAULT NULL COMMENT '绑定的设备码（一机一卡）',
  `activate_time` DATETIME DEFAULT NULL COMMENT '激活时间',
  `expire_time` DATETIME DEFAULT NULL COMMENT '过期时间',
  `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '卡密创建时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='钓鱼脚本卡密表';
