-- ============================================================
-- 重点人管控系统 - MySQL 初始化脚本
-- 数据库: wcnr
-- 根据 Navicat 截图重构
-- ============================================================

CREATE DATABASE IF NOT EXISTS wcnr DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE wcnr;

-- ==================== 布控人员表 ====================
DROP TABLE IF EXISTS young_peoples;
CREATE TABLE young_peoples (
    id                      INT AUTO_INCREMENT PRIMARY KEY COMMENT 'ID',
    name                    VARCHAR(255) DEFAULT NULL COMMENT '姓名',
    gender                  VARCHAR(255) DEFAULT NULL COMMENT '性别',
    contact                 VARCHAR(255) DEFAULT NULL COMMENT '联系方式',
    id_card_number          VARCHAR(255) DEFAULT NULL COMMENT '身份证号码',
    address                 VARCHAR(255) DEFAULT NULL COMMENT '居住地详址',
    person_category         VARCHAR(255) DEFAULT NULL COMMENT '人员类别',
    criminal_record         VARCHAR(255) DEFAULT NULL COMMENT '涉案前科',
    update_time             VARCHAR(255) DEFAULT NULL COMMENT '更新时间',
    person_face_url         LONGTEXT DEFAULT NULL COMMENT '原始人脸URL',
    last_capture_query_time DATETIME DEFAULT NULL COMMENT '最后一次抓拍查询时间',
    age                     VARCHAR(255) DEFAULT NULL COMMENT '年龄',
    police_station          VARCHAR(255) DEFAULT NULL COMMENT '派出所',
    police_district         VARCHAR(255) DEFAULT NULL COMMENT '警务区',
    control_category        VARCHAR(255) DEFAULT NULL COMMENT '管控类别',
    control_time            VARCHAR(255) DEFAULT NULL COMMENT '纳管时间',
    INDEX idx_id_card_number (id_card_number),
    INDEX idx_name (name),
    INDEX idx_police_station (police_station),
    INDEX idx_control_category (control_category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='布控人员表';


-- ==================== 预警抓拍记录表 ====================
DROP TABLE IF EXISTS capture_records;
CREATE TABLE capture_records (
    id                  BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT 'ID',
    person_id_card      VARCHAR(18) DEFAULT NULL COMMENT '身份证号码',
    person_face_url     TEXT DEFAULT NULL COMMENT '原始人脸URL',
    capture_id          VARCHAR(255) DEFAULT NULL COMMENT '抓拍唯一ID',
    capture_time        DATETIME DEFAULT NULL COMMENT '抓拍时间',
    camera_name         VARCHAR(255) DEFAULT NULL COMMENT '摄像头名称',
    camera_index_code   VARCHAR(100) DEFAULT NULL COMMENT '摄像头编号',
    face_pic_url        TEXT DEFAULT NULL COMMENT '抓拍人脸图',
    bkg_url             TEXT DEFAULT NULL COMMENT '全景图',
    similarity          FLOAT DEFAULT NULL COMMENT '相似度',
    gender              VARCHAR(10) DEFAULT NULL COMMENT '性别',
    age_group           VARCHAR(20) DEFAULT NULL COMMENT '年龄组',
    glass               VARCHAR(10) DEFAULT NULL COMMENT '是否戴眼镜',
    plate_no            VARCHAR(20) DEFAULT NULL COMMENT '车牌号',
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    is_processed        TINYINT DEFAULT 0 COMMENT '是否已处理: 0否 1是',
    INDEX idx_person_id_card (person_id_card),
    INDEX idx_capture_time (capture_time),
    INDEX idx_capture_id (capture_id),
    INDEX idx_camera_index_code (camera_index_code),
    INDEX idx_is_processed (is_processed)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='预警抓拍记录表';


-- ==================== 任务状态表 ====================
DROP TABLE IF EXISTS task_status;
CREATE TABLE task_status (
    task_name       VARCHAR(255) NOT NULL PRIMARY KEY COMMENT '任务名称',
    last_run_time   DATETIME NOT NULL COMMENT '最后运行时间',
    last_run_hash   VARCHAR(64) DEFAULT NULL COMMENT '最后运行哈希',
    status          VARCHAR(50) DEFAULT NULL COMMENT '状态'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='任务状态表';


-- ==================== 临时导入表 ====================
DROP TABLE IF EXISTS tmp;
CREATE TABLE tmp (
    序号              VARCHAR(255) DEFAULT NULL COMMENT '序号',
    姓名              VARCHAR(255) DEFAULT NULL COMMENT '姓名',
    公民身份证号码    VARCHAR(255) DEFAULT NULL COMMENT '公民身份证号码',
    人员类别          VARCHAR(255) DEFAULT NULL COMMENT '人员类别',
    f5                VARCHAR(255) DEFAULT NULL,
    f6                VARCHAR(255) DEFAULT NULL,
    f7                VARCHAR(255) DEFAULT NULL,
    f8                VARCHAR(255) DEFAULT NULL,
    f9                VARCHAR(255) DEFAULT NULL,
    f10               VARCHAR(255) DEFAULT NULL,
    f11               VARCHAR(255) DEFAULT NULL,
    f12               VARCHAR(255) DEFAULT NULL,
    f13               VARCHAR(255) DEFAULT NULL,
    f14               VARCHAR(255) DEFAULT NULL,
    f15               VARCHAR(255) DEFAULT NULL,
    f16               VARCHAR(255) DEFAULT NULL,
    f17               VARCHAR(255) DEFAULT NULL,
    f18               VARCHAR(255) DEFAULT NULL,
    f19               VARCHAR(255) DEFAULT NULL,
    f20               VARCHAR(255) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='临时导入表';


-- ==================== 摄像头类型表 ====================
DROP TABLE IF EXISTS cameras_type;
CREATE TABLE cameras_type (
    id          INT AUTO_INCREMENT PRIMARY KEY COMMENT 'ID',
    type_name   VARCHAR(100) NOT NULL COMMENT '类型名称',
    type_code   VARCHAR(50) DEFAULT NULL COMMENT '类型编码',
    description VARCHAR(255) DEFAULT NULL COMMENT '描述',
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='摄像头类型表';


-- ==================== 摄像头设备表 ====================
DROP TABLE IF EXISTS cameras;
CREATE TABLE cameras (
    id                  INT AUTO_INCREMENT PRIMARY KEY COMMENT 'ID',
    camera_name         VARCHAR(255) NOT NULL COMMENT '摄像头名称',
    camera_index_code   VARCHAR(100) NOT NULL UNIQUE COMMENT '摄像头编号(唯一)',
    camera_type_id      INT DEFAULT NULL COMMENT '摄像头类型ID',
    location            VARCHAR(255) DEFAULT NULL COMMENT '安装位置',
    longitude           DECIMAL(10,7) DEFAULT NULL COMMENT '经度',
    latitude            DECIMAL(10,7) DEFAULT NULL COMMENT '纬度',
    ip_address          VARCHAR(50) DEFAULT NULL COMMENT 'IP地址',
    status              TINYINT DEFAULT 1 COMMENT '状态: 0离线 1在线',
    install_time        DATETIME DEFAULT NULL COMMENT '安装时间',
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_camera_index_code (camera_index_code),
    INDEX idx_camera_type_id (camera_type_id),
    INDEX idx_status (status),
    FOREIGN KEY (camera_type_id) REFERENCES cameras_type(id) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='摄像头设备表';


-- ==================== 插入演示数据 ====================

-- 摄像头类型演示数据
INSERT INTO cameras_type (type_name, type_code, description) VALUES
('人脸卡口', 'FACE_CAPTURE', '人脸抓拍专用摄像头'),
('车辆卡口', 'VEHICLE_CAPTURE', '车辆抓拍专用摄像头'),
('治安监控', 'SECURITY', '普通治安监控摄像头'),
('高点监控', 'HIGH_POINT', '高空瞭望摄像头');

-- 摄像头设备演示数据
INSERT INTO cameras (camera_name, camera_index_code, camera_type_id, location, longitude, latitude, ip_address, status, install_time) VALUES
('城中广场人脸卡口01', 'CAM_001', 1, '城中区广场东路与解放北路交叉口', 109.4280, 24.3260, '192.168.1.101', 1, '2025-06-01 08:00:00'),
('鱼峰公园人脸卡口02', 'CAM_002', 1, '鱼峰区鱼峰路公园正门口', 109.4350, 24.3120, '192.168.1.102', 1, '2025-06-01 08:00:00'),
('柳南车辆卡口01', 'CAM_003', 2, '柳南区柳邕路与航岭路交叉口', 109.4050, 24.3050, '192.168.1.103', 1, '2025-07-15 09:00:00'),
('柳北治安监控01', 'CAM_004', 3, '柳北区跃进路与北雀路交叉口', 109.4150, 24.3350, '192.168.1.104', 1, '2025-08-01 10:00:00'),
('柳江高点监控01', 'CAM_005', 4, '柳江区柳江大道政府大楼顶', 109.3850, 24.2650, '192.168.1.105', 0, '2025-09-01 08:30:00'),
('城中广场人脸卡口06', 'CAM_006', 1, '城中区龙城路与五一路交叉口', 109.4250, 24.3220, '192.168.1.106', 1, '2025-06-15 08:00:00'),
('鱼峰治安监控02', 'CAM_007', 3, '鱼峰区荣军路与屏山大道交叉口', 109.4400, 24.3080, '192.168.1.107', 1, '2025-08-15 09:30:00'),
('柳南人脸卡口03', 'CAM_008', 1, '柳南区飞鹅路与南站路交叉口', 109.4000, 24.3100, '192.168.1.108', 1, '2025-07-01 08:00:00');

-- 布控人员演示数据 (60条)
INSERT INTO young_peoples (id_card_number, name, gender, contact, age, address, person_category, criminal_record, police_station, police_district, control_category, control_time, last_capture_query_time) VALUES
('450202199001011234', '张伟', '男', '13800001001', '36', '柳州市城中区解放北路1号', '重点人员', NULL, '城中派出所', '城中警务区', '重点管控', '2025-01-15', '2026-04-25 08:30:00'),
('450202199002021234', '王芳', '女', '13800001002', '34', '柳州市鱼峰区鱼峰路2号', '重点人员', NULL, '鱼峰派出所', '鱼峰警务区', '重点管控', '2025-02-20', '2026-04-25 09:15:00'),
('450202199003031234', '李娜', '女', '13800001003', '36', '柳州市柳南区柳邕路3号', '涉毒人员', '吸毒前科', '柳南派出所', '柳南警务区', '重点管控', '2025-03-10', NULL),
('450202199004041234', '刘洋', '男', '13800001004', '36', '柳州市柳北区跃进路4号', '重点人员', NULL, '柳北派出所', '柳北警务区', '一般管控', '2025-01-20', '2026-04-25 07:00:00'),
('450202199005051234', '陈静', '女', '13800001005', '35', '柳州市柳江区柳江路5号', '重点人员', NULL, '柳江派出所', '柳江警务区', '重点管控', '2025-04-05', NULL),
('450202199006061234', '杨明', '男', '13800001006', '35', '柳州市城中区中山路6号', '涉毒人员', '贩毒前科', '城中派出所', '城中警务区', '重点管控', '2025-02-28', '2026-04-25 10:00:00'),
('450202199007071234', '赵强', '男', '13800001007', '35', '柳州市鱼峰区驾鹤路7号', '重点人员', NULL, '鱼峰派出所', '鱼峰警务区', '一般管控', '2025-03-15', NULL),
('450202199008081234', '黄磊', '男', '13800001008', '35', '柳州市柳南区壶西大道8号', '重点人员', NULL, '柳南派出所', '柳南警务区', '重点管控', '2025-01-10', '2026-04-25 11:30:00'),
('450202199009091234', '周杰', '男', '13800001009', '35', '柳州市柳北区白露大道9号', '前科人员', '盗窃前科', '柳北派出所', '柳北警务区', '一般管控', '2025-05-01', NULL),
('450202199010101234', '吴刚', '男', '13800001010', '35', '柳州市柳江区瑞龙路10号', '重点人员', NULL, '柳江派出所', '柳江警务区', '重点管控', '2025-02-15', '2026-04-25 06:45:00'),
('450202199101111234', '徐丽', '女', '13800001011', '35', '柳州市城中区广场路11号', '涉毒人员', '吸毒前科', '城中派出所', '城中警务区', '重点管控', '2025-04-20', NULL),
('450202199102121234', '孙涛', '男', '13800001012', '34', '柳州市鱼峰区荣军路12号', '重点人员', NULL, '鱼峰派出所', '鱼峰警务区', '一般管控', '2025-03-01', '2026-04-25 14:20:00'),
('450202199103131234', '马超', '男', '13800001013', '33', '柳州市柳南区航岭路13号', '重点人员', NULL, '柳南派出所', '柳南警务区', '待审批', '2025-06-01', NULL),
('450202199104141234', '朱红', '女', '13800001014', '32', '柳州市柳北区北雀路14号', '前科人员', '故意伤害前科', '柳北派出所', '柳北警务区', '重点管控', '2025-01-25', NULL),
('450202199105151234', '胡平', '男', '13800001015', '31', '柳州市柳江区成团路15号', '重点人员', NULL, '柳江派出所', '柳江警务区', '一般管控', '2025-05-10', '2026-04-25 13:00:00'),
('450202199106161234', '郭亮', '男', '13800001016', '30', '柳州市城中区八一路16号', '涉毒人员', '吸毒前科', '城中派出所', '城中警务区', '重点管控', '2025-02-10', NULL),
('450202199107171234', '林霞', '女', '13800001017', '29', '柳州市鱼峰区鸡喇路17号', '重点人员', NULL, '鱼峰派出所', '鱼峰警务区', '一般管控', '2025-04-01', '2026-04-25 15:10:00'),
('450202199108181234', '何勇', '男', '13800001018', '28', '柳州市柳南区潭中西路18号', '重点人员', NULL, '柳南派出所', '柳南警务区', '已撤控', '2025-01-05', NULL),
('450202199109191234', '高明', '男', '13800001019', '27', '柳州市柳北区雅儒路19号', '前科人员', '抢劫前科', '柳北派出所', '柳北警务区', '重点管控', '2025-03-20', '2026-04-25 09:50:00'),
('450202199110201234', '罗辉', '男', '13800001020', '26', '柳州市柳江区拉堡镇20号', '重点人员', NULL, '柳江派出所', '柳江警务区', '一般管控', '2025-05-20', NULL),
('450202199201011235', '韩雪', '女', '13800002001', '34', '柳州市城中区公园路21号', '涉毒人员', '吸毒前科', '公园派出所', '公园警务区', '重点管控', '2025-02-05', '2026-04-24 18:30:00'),
('450202199202021235', '冯刚', '男', '13800002002', '34', '柳州市鱼峰区麒麟路22号', '重点人员', NULL, '麒麟派出所', '麒麟警务区', '一般管控', '2025-01-15', NULL),
('450202199203031235', '曹敏', '女', '13800002003', '33', '柳州市柳南区南站路23号', '重点人员', NULL, '南站派出所', '南站警务区', '待审批', '2025-06-10', NULL),
('450202199204041235', '彭勇', '男', '13800002004', '32', '柳州市柳北区雀儿山路24号', '前科人员', '盗窃前科', '雀儿山派出所', '雀儿山警务区', '重点管控', '2025-03-05', '2026-04-25 12:00:00'),
('450202199205051235', '邓丽', '女', '13800002005', '31', '柳州市柳江区进德路25号', '重点人员', NULL, '进德派出所', '进德警务区', '一般管控', '2025-04-15', NULL),
('450202199206061235', '许峰', '男', '13800002006', '30', '柳州市城中区中南路26号', '涉毒人员', '贩毒前科', '中南派出所', '中南警务区', '重点管控', '2025-02-25', '2026-04-25 16:00:00'),
('450202199207071235', '傅磊', '男', '13800002007', '29', '柳州市鱼峰区白莲路27号', '重点人员', NULL, '白莲派出所', '白莲警务区', '一般管控', '2025-05-05', NULL),
('450202199208081235', '沈静', '女', '13800002008', '28', '柳州市柳南区银山路28号', '重点人员', NULL, '银山派出所', '银山警务区', '已撤控', '2025-01-30', NULL),
('450202199209091235', '曾杰', '男', '13800002009', '27', '柳州市柳北区长塘路29号', '前科人员', '故意伤害前科', '长塘派出所', '长塘警务区', '重点管控', '2025-04-10', '2026-04-25 08:00:00'),
('450202199210101235', '吕刚', '男', '13800002010', '26', '柳州市柳江区百朋路30号', '重点人员', NULL, '百朋派出所', '百朋警务区', '一般管控', '2025-03-25', NULL),
('450202199301111235', '苏瑶', '女', '13800003001', '33', '柳州市城中区潭中大道31号', '涉毒人员', '吸毒前科', '潭中派出所', '潭中警务区', '重点管控', '2025-02-15', '2026-04-25 07:30:00'),
('450202199302121235', '卢强', '男', '13800003002', '33', '柳州市鱼峰区五里亭路32号', '重点人员', NULL, '五里亭派出所', '五里亭警务区', '一般管控', '2025-01-20', NULL),
('450202199303131235', '蒋敏', '女', '13800003003', '33', '柳州市柳南区鹅山路33号', '重点人员', NULL, '鹅山派出所', '鹅山警务区', '重点管控', '2025-05-15', '2026-04-25 10:30:00'),
('450202199304141235', '蔡勇', '男', '13800003004', '32', '柳州市柳北区沙塘路34号', '前科人员', '抢劫前科', '沙塘派出所', '沙塘警务区', '重点管控', '2025-03-10', NULL),
('450202199305151235', '贾丽', '女', '13800003005', '31', '柳州市柳江区三都路35号', '重点人员', NULL, '三都派出所', '三都警务区', '一般管控', '2025-04-25', NULL),
('450202199306161235', '丁峰', '男', '13800003006', '30', '柳州市城中区河东路36号', '涉毒人员', '吸毒前科', '河东派出所', '河东警务区', '重点管控', '2025-02-01', '2026-04-24 20:00:00'),
('450202199307171235', '魏磊', '男', '13800003007', '29', '柳州市鱼峰区箭盘山路37号', '重点人员', NULL, '箭盘山派出所', '箭盘山警务区', '待审批', '2025-06-05', NULL),
('450202199308181235', '薛静', '女', '13800003008', '28', '柳州市柳南区河西路38号', '重点人员', NULL, '河西派出所', '河西警务区', '重点管控', '2025-01-10', '2026-04-25 11:00:00'),
('450202199309191235', '叶杰', '男', '13800003009', '27', '柳州市柳北区钢城路39号', '前科人员', '盗窃前科', '钢城派出所', '钢城警务区', '一般管控', '2025-05-20', NULL),
('450202199310201235', '阎刚', '男', '13800003010', '26', '柳州市柳江区穿山路40号', '重点人员', NULL, '穿山派出所', '穿山警务区', '重点管控', '2025-03-15', NULL),
('450202199401011236', '余瑶', '女', '13800004001', '32', '柳州市城中区龙城路41号', '涉毒人员', '吸毒前科', '中南派出所', '中南警务区', '已撤控', '2025-04-05', NULL),
('450202199402021236', '潘强', '男', '13800004002', '32', '柳州市鱼峰区柳石路42号', '重点人员', NULL, '白莲派出所', '白莲警务区', '一般管控', '2025-02-20', '2026-04-25 14:00:00'),
('450202199403031236', '杜敏', '女', '13800004003', '32', '柳州市柳南区柳石路43号', '重点人员', NULL, '柳石派出所', '柳石警务区', '重点管控', '2025-01-05', NULL),
('450202199404041236', '戴勇', '男', '13800004004', '32', '柳州市柳北区胜利路44号', '前科人员', '故意伤害前科', '胜利派出所', '胜利警务区', '重点管控', '2025-03-30', '2026-04-25 08:45:00'),
('450202199405051236', '夏丽', '女', '13800004005', '31', '柳州市柳江区里高路45号', '重点人员', NULL, '里高派出所', '里高警务区', '一般管控', '2025-05-10', NULL),
('450202199406061236', '姜峰', '男', '13800004006', '30', '柳州市城中区三中路46号', '涉毒人员', '贩毒前科', '潭中派出所', '潭中警务区', '重点管控', '2025-02-10', '2026-04-24 22:00:00'),
('450202199407171236', '钱磊', '男', '13800004007', '29', '柳州市鱼峰区荣军路47号', '重点人员', NULL, '五里亭派出所', '五里亭警务区', '一般管控', '2025-04-20', NULL),
('450202199408181236', '秦静', '女', '13800004008', '28', '柳州市柳南区红光路48号', '重点人员', NULL, '鹅山派出所', '鹅山警务区', '重点管控', '2025-01-25', '2026-04-25 15:30:00'),
('450202199409191236', '尤杰', '男', '13800004009', '27', '柳州市柳北区北雀路49号', '前科人员', '抢劫前科', '雀儿山派出所', '雀儿山警务区', '一般管控', '2025-03-15', NULL),
('450202199410201236', '许刚', '男', '13800004010', '26', '柳州市柳江区百朋路50号', '重点人员', NULL, '百朋派出所', '百朋警务区', '重点管控', '2025-05-25', NULL),
('450202199501011237', '何瑶', '女', '13800005001', '31', '柳州市城中区弯塘路51号', '涉毒人员', '吸毒前科', '公园派出所', '公园警务区', '重点管控', '2025-02-28', '2026-04-25 09:00:00'),
('450202199502021237', '吕强', '男', '13800005002', '31', '柳州市鱼峰区文笔路52号', '重点人员', NULL, '麒麟派出所', '麒麟警务区', '一般管控', '2025-04-01', NULL),
('450202199503031237', '施敏', '女', '13800005003', '31', '柳州市柳南区飞鹅路53号', '重点人员', NULL, '南站派出所', '南站警务区', '重点管控', '2025-01-15', '2026-04-25 10:15:00'),
('450202199504141237', '张勇', '男', '13800005004', '31', '柳州市柳北区沙塘路54号', '前科人员', '盗窃前科', '沙塘派出所', '沙塘警务区', '已撤控', '2025-05-01', NULL),
('450202199505151237', '孔丽', '女', '13800005005', '30', '柳州市柳江区进德路55号', '重点人员', NULL, '进德派出所', '进德警务区', '一般管控', '2025-03-20', NULL),
('450202199506161237', '曹峰', '男', '13800005006', '29', '柳州市城中区河东路56号', '涉毒人员', '吸毒前科', '河东派出所', '河东警务区', '待审批', '2025-06-15', NULL),
('450202199507171237', '严磊', '男', '13800005007', '29', '柳州市鱼峰区东环路57号', '重点人员', NULL, '箭盘山派出所', '箭盘山警务区', '一般管控', '2025-04-10', '2026-04-25 16:30:00'),
('450202199508181237', '华静', '女', '13800005008', '30', '柳州市柳南区壶西大道58号', '重点人员', NULL, '河西派出所', '河西警务区', '重点管控', '2025-02-05', NULL),
('450202199509191237', '金杰', '男', '13800005009', '29', '柳州市柳北区长虹路59号', '前科人员', '故意伤害前科', '长塘派出所', '长塘警务区', '一般管控', '2025-05-05', NULL),
('450202199510201237', '魏刚', '男', '13800005010', '30', '柳州市柳江区穿山路60号', '重点人员', NULL, '穿山派出所', '穿山警务区', '重点管控', '2025-03-01', NULL);


-- 预警记录演示数据 (过去30天, 约4400条, 用存储过程批量生成)
DELIMITER //

DROP PROCEDURE IF EXISTS generate_capture_records //

CREATE PROCEDURE generate_capture_records()
BEGIN
    DECLARE i INT DEFAULT 0;
    DECLARE day_offset INT;
    DECLARE daily_count INT;
    DECLARE j INT;
    DECLARE alert_time DATETIME;
    DECLARE person_id VARCHAR(18);
    DECLARE cam_name VARCHAR(50);
    DECLARE cam_code VARCHAR(100);
    DECLARE is_proc TINYINT;
    DECLARE sim_val FLOAT;
    DECLARE has_plate INT;
    DECLARE base_date DATETIME;
    DECLARE p_gender VARCHAR(10);
    DECLARE p_age_group VARCHAR(20);

    SET base_date = '2026-04-25 23:59:59';

    SET day_offset = 30;
    WHILE day_offset >= 0 DO
        SET daily_count = FLOOR(80 + RAND() * 120);
        SET j = 0;

        WHILE j < daily_count DO
            SET alert_time = DATE_SUB(DATE(base_date), INTERVAL day_offset DAY)
                + INTERVAL FLOOR(RAND() * 24) HOUR
                + INTERVAL FLOOR(RAND() * 60) MINUTE
                + INTERVAL FLOOR(RAND() * 60) SECOND;

            -- 随机选一个布控人员
            SELECT id_card_number, gender,
                   CASE
                       WHEN age < 18 THEN '少年'
                       WHEN age < 30 THEN '青年'
                       WHEN age < 40 THEN '中青年'
                       WHEN age < 50 THEN '中年'
                       ELSE '中老年'
                   END
            INTO person_id, p_gender, p_age_group FROM young_peoples
                ORDER BY RAND() LIMIT 1;

            -- 随机选一个摄像头
            SELECT camera_name, camera_index_code INTO cam_name, cam_code FROM cameras
                ORDER BY RAND() LIMIT 1;

            SET sim_val = ROUND(0.85 + RAND() * 0.149, 3);
            SET has_plate = FLOOR(RAND() * 3);

            -- 历史数据大部分已处理
            IF day_offset > 3 THEN
                SET is_proc = ELT(1 + FLOOR(RAND() * 100) / 100 * 4,
                    2, 2, 2, 1, 1, 1, 3, 0);
                IF is_proc IS NULL THEN SET is_proc = 2; END IF;
            ELSE
                SET is_proc = FLOOR(RAND() * 4);
            END IF;

            INSERT INTO capture_records
                (capture_id, person_id_card, person_face_url, capture_time, camera_name, camera_index_code, face_pic_url, bkg_url, similarity, gender, age_group, glass, plate_no, is_processed)
            VALUES (
                CONCAT('YW', DATE_FORMAT(alert_time, '%Y%m%d%H%i%s'), FLOOR(1000 + RAND() * 8999)),
                person_id,
                NULL,
                alert_time,
                cam_name,
                cam_code,
                NULL,
                NULL,
                sim_val,
                p_gender,
                p_age_group,
                IF(FLOOR(RAND() * 2) = 0, '是', '否'),
                IF(has_plate = 0, CONCAT('桂B', LPAD(FLOOR(RAND() * 99999), 5, '0')), NULL),
                is_proc
            );

            SET j = j + 1;
        END WHILE;

        SET day_offset = day_offset - 1;
    END WHILE;
END //

DELIMITER ;

CALL generate_capture_records();
DROP PROCEDURE IF EXISTS generate_capture_records;

-- 初始化任务状态
INSERT INTO task_status (task_name, last_run_time, last_run_hash, status) VALUES
('capture_sync', '2026-04-25 00:00:00', NULL, 'running'),
('person_sync', '2026-04-25 00:00:00', NULL, 'idle');

-- 验证
SELECT 'young_peoples' AS tbl, COUNT(*) AS cnt FROM young_peoples
UNION ALL
SELECT 'capture_records', COUNT(*) FROM capture_records
UNION ALL
SELECT 'cameras', COUNT(*) FROM cameras
UNION ALL
SELECT 'cameras_type', COUNT(*) FROM cameras_type
UNION ALL
SELECT 'task_status', COUNT(*) FROM task_status;


-- ==================== 线索管理表 ====================
CREATE TABLE IF NOT EXISTS clues (
    id                  INT AUTO_INCREMENT PRIMARY KEY COMMENT 'ID',
    clue_number         VARCHAR(100) NOT NULL COMMENT '线索编号',
    title               VARCHAR(500) DEFAULT NULL COMMENT '线索标题',
    content_cr_id       TEXT DEFAULT NULL COMMENT '关联抓拍记录ID(逗号分隔)',
    issue_date          DATE DEFAULT NULL COMMENT '下发日期',
    deadline            DATE DEFAULT NULL COMMENT '截止日期',
    status              VARCHAR(50) DEFAULT 'pending' COMMENT '状态: pending/in_progress/completed',
    responsible_officer VARCHAR(100) DEFAULT NULL COMMENT '负责民警',
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_clue_number (clue_number),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='线索管理表';


-- ==================== 同行人聚类临时表 ====================
CREATE TABLE IF NOT EXISTS temp_companion_groups (
    id                  INT AUTO_INCREMENT PRIMARY KEY COMMENT 'ID',
    capture_ids         TEXT DEFAULT NULL COMMENT '抓拍记录ID列表',
    group_id            VARCHAR(100) DEFAULT NULL COMMENT '聚类组ID',
    camera_index_code   VARCHAR(100) DEFAULT NULL COMMENT '摄像头编号',
    camera_name         VARCHAR(255) DEFAULT NULL COMMENT '摄像头名称',
    start_time          DATETIME DEFAULT NULL COMMENT '开始时间',
    end_time            DATETIME DEFAULT NULL COMMENT '结束时间',
    member_count        INT DEFAULT 0 COMMENT '成员数量',
    members             TEXT DEFAULT NULL COMMENT '成员身份证号(逗号分隔)',
    bkg_urls            TEXT DEFAULT NULL COMMENT '背景图URL列表(逗号分隔)',
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_group_id (group_id),
    INDEX idx_camera_index_code (camera_index_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='同行人聚类临时表';


-- ==================== 人脸记录表 ====================
CREATE TABLE IF NOT EXISTS face_records (
    id                  VARCHAR(255) NOT NULL PRIMARY KEY COMMENT '记录ID',
    name                VARCHAR(255) DEFAULT NULL COMMENT '姓名',
    certificateNumber   VARCHAR(18) DEFAULT NULL COMMENT '身份证号',
    plateNo             VARCHAR(20) DEFAULT NULL COMMENT '车牌号',
    cameraName          VARCHAR(255) DEFAULT NULL COMMENT '摄像头名称',
    cameraIndexCode     VARCHAR(100) DEFAULT NULL COMMENT '摄像头编号',
    captureTime         DATETIME DEFAULT NULL COMMENT '抓拍时间',
    bkgUrl              TEXT DEFAULT NULL COMMENT '背景图URL',
    facePicUrl          TEXT DEFAULT NULL COMMENT '人脸图URL',
    genderName          VARCHAR(10) DEFAULT NULL COMMENT '性别',
    similarity          FLOAT DEFAULT NULL COMMENT '相似度',
    INDEX idx_certificate (certificateNumber),
    INDEX idx_capture_time (captureTime)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='人脸记录表';


-- ==================== 驾驶员状态表 ====================
CREATE TABLE IF NOT EXISTS driver_status (
    id                  INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    cr_id               INT DEFAULT NULL COMMENT '抓拍记录ID',
    is_driver           TINYINT DEFAULT NULL COMMENT '是否为驾驶员: 0否 1是',
    created_at          TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_id (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='驾驶员状态表';


-- ==================== 临时摄像头表 ====================
CREATE TABLE IF NOT EXISTS tmp_cameras (
    id                  INT AUTO_INCREMENT PRIMARY KEY COMMENT 'ID',
    cameraIndexCode     VARCHAR(100) DEFAULT NULL COMMENT '摄像头编号',
    gbIndexCode         VARCHAR(100) DEFAULT NULL COMMENT '国标编号',
    name                VARCHAR(255) DEFAULT NULL COMMENT '摄像头名称',
    deviceIndexCode     VARCHAR(100) DEFAULT NULL COMMENT '设备编号',
    longitude           DECIMAL(10,7) DEFAULT NULL COMMENT '经度',
    latitude            DECIMAL(10,7) DEFAULT NULL COMMENT '纬度',
    altitude            DECIMAL(10,2) DEFAULT NULL COMMENT '海拔',
    pixel               VARCHAR(50) DEFAULT NULL COMMENT '像素',
    cameraType          VARCHAR(50) DEFAULT NULL COMMENT '摄像头类型',
    cameraTypeName      VARCHAR(100) DEFAULT NULL COMMENT '摄像头类型名称',
    channelNo           INT DEFAULT NULL COMMENT '通道号',
    capability          VARCHAR(255) DEFAULT NULL COMMENT '能力',
    subStream           VARCHAR(50) DEFAULT NULL COMMENT '子码流',
    channels            VARCHAR(255) DEFAULT NULL COMMENT '通道',
    installLocation     VARCHAR(255) DEFAULT NULL COMMENT '安装位置',
    capabilitiySet      VARCHAR(255) DEFAULT NULL,
    microphoneCapability VARCHAR(50) DEFAULT NULL,
    intelligentSet      VARCHAR(255) DEFAULT NULL,
    intelligentSetName  VARCHAR(255) DEFAULT NULL,
    deviceType          VARCHAR(50) DEFAULT NULL,
    deviceTypeName      VARCHAR(100) DEFAULT NULL,
    deviceCategory      VARCHAR(50) DEFAULT NULL,
    deviceCategoryName  VARCHAR(100) DEFAULT NULL,
    deviceCatalog       VARCHAR(50) DEFAULT NULL,
    deviceCatalogName   VARCHAR(100) DEFAULT NULL,
    createTime          DATETIME DEFAULT NULL,
    updateTime          DATETIME DEFAULT NULL,
    unitIndexCode       VARCHAR(100) DEFAULT NULL,
    treatyType          VARCHAR(50) DEFAULT NULL,
    treatyTypeName      VARCHAR(100) DEFAULT NULL,
    treatyTypeCode      VARCHAR(50) DEFAULT NULL,
    status              VARCHAR(20) DEFAULT NULL,
    statusName          VARCHAR(50) DEFAULT NULL,
    INDEX idx_camera_index_code (cameraIndexCode)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='临时摄像头表';


-- ==================== 用户管理表 ====================
CREATE TABLE IF NOT EXISTS users (
    id                  INT AUTO_INCREMENT PRIMARY KEY COMMENT 'ID',
    username            VARCHAR(100) NOT NULL UNIQUE COMMENT '用户名',
    password            VARCHAR(255) NOT NULL COMMENT '密码(bcrypt哈希)',
    real_name           VARCHAR(100) DEFAULT NULL COMMENT '真实姓名',
    role                VARCHAR(50) DEFAULT 'operator' COMMENT '角色: admin/operator',
    police_station      VARCHAR(255) DEFAULT NULL COMMENT '所属派出所',
    is_active           TINYINT DEFAULT 1 COMMENT '是否启用: 0停用 1启用',
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_username (username),
    INDEX idx_role (role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户管理表';

-- 默认管理员账户 (密码: admin123)
INSERT INTO users (username, password, real_name, role) VALUES
('admin', '$2b$12$uhELeUY1sITxukkldaAqJu43L5sKXWhHnv27vy4rdfGzRYHUZKNXu', '系统管理员', 'admin');


-- ==================== 人口系统导入数据表 ====================
CREATE TABLE IF NOT EXISTS population_info (
    id                  INT AUTO_INCREMENT PRIMARY KEY COMMENT 'ID',
    id_card_number      VARCHAR(18) NOT NULL COMMENT '身份证号',
    name                VARCHAR(255) DEFAULT NULL COMMENT '姓名',
    gender              VARCHAR(10) DEFAULT NULL COMMENT '性别',
    age                 VARCHAR(10) DEFAULT NULL COMMENT '年龄',
    address             VARCHAR(500) DEFAULT NULL COMMENT '住址',
    contact             VARCHAR(255) DEFAULT NULL COMMENT '联系方式',
    import_log_id       INT DEFAULT NULL COMMENT '来源导入记录ID',
    promoted            TINYINT DEFAULT 0 COMMENT '是否已纳入布控: 0否 1是',
    promoted_at         DATETIME DEFAULT NULL COMMENT '纳入布控时间',
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '导入时间',
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uk_id_card_number (id_card_number),
    INDEX idx_name (name),
    INDEX idx_promoted (promoted),
    INDEX idx_import_log_id (import_log_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='人口系统导入数据表';


-- ==================== 警综系统案件数据表 ====================
CREATE TABLE IF NOT EXISTS cases (
    id                  INT AUTO_INCREMENT PRIMARY KEY COMMENT 'ID',
    case_number         VARCHAR(100) NOT NULL COMMENT '案件编号',
    case_name           VARCHAR(500) DEFAULT NULL COMMENT '案件名称',
    case_type           VARCHAR(100) DEFAULT NULL COMMENT '案件类型',
    incident_time       DATETIME DEFAULT NULL COMMENT '案发时间',
    incident_location   VARCHAR(500) DEFAULT NULL COMMENT '案发地点',
    description         TEXT DEFAULT NULL COMMENT '案件描述(扩展字段)',
    import_log_id       INT DEFAULT NULL COMMENT '来源导入记录ID',
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '导入时间',
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uk_case_number (case_number),
    INDEX idx_case_type (case_type),
    INDEX idx_incident_time (incident_time),
    INDEX idx_import_log_id (import_log_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='警综系统案件数据表';


-- ==================== 案件-涉案人员关联表 ====================
CREATE TABLE IF NOT EXISTS case_persons (
    id                  INT AUTO_INCREMENT PRIMARY KEY COMMENT 'ID',
    case_id             INT NOT NULL COMMENT '案件ID',
    id_card_number      VARCHAR(18) NOT NULL COMMENT '涉案人员身份证号',
    person_name         VARCHAR(255) DEFAULT NULL COMMENT '涉案人员姓名(冗余)',
    person_source       VARCHAR(20) DEFAULT 'unknown' COMMENT '人员来源: young_peoples/population_info/unknown',
    role_in_case        VARCHAR(100) DEFAULT NULL COMMENT '涉案角色(嫌疑人/受害人/证人等)',
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    UNIQUE KEY uk_case_person (case_id, id_card_number),
    INDEX idx_id_card_number (id_card_number),
    INDEX idx_person_source (person_source),
    FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='案件-涉案人员关联表';


-- ==================== 数据导入日志表 ====================
CREATE TABLE IF NOT EXISTS data_import_logs (
    id                  INT AUTO_INCREMENT PRIMARY KEY COMMENT 'ID',
    source_system       VARCHAR(50) NOT NULL COMMENT '来源系统: jingzong/renkou',
    file_name           VARCHAR(500) NOT NULL COMMENT '原始文件名',
    file_size           INT DEFAULT NULL COMMENT '文件大小(字节)',
    record_count        INT DEFAULT 0 COMMENT '导入记录数',
    success_count       INT DEFAULT 0 COMMENT '成功记录数',
    fail_count          INT DEFAULT 0 COMMENT '失败记录数',
    duplicate_count     INT DEFAULT 0 COMMENT '重复跳过记录数',
    status              VARCHAR(20) DEFAULT 'pending' COMMENT '状态: pending/processing/completed/failed',
    error_message       TEXT DEFAULT NULL COMMENT '错误信息',
    operator_id         INT DEFAULT NULL COMMENT '操作人用户ID',
    operator_name       VARCHAR(100) DEFAULT NULL COMMENT '操作人姓名',
    started_at          DATETIME DEFAULT NULL COMMENT '开始处理时间',
    completed_at        DATETIME DEFAULT NULL COMMENT '完成处理时间',
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_source_system (source_system),
    INDEX idx_status (status),
    INDEX idx_operator_id (operator_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='数据导入日志表';


-- ==================== 人口数据导入暂存表 ====================
CREATE TABLE IF NOT EXISTS population_staging (
    id                  INT AUTO_INCREMENT PRIMARY KEY COMMENT 'ID',
    import_log_id       INT DEFAULT NULL COMMENT '关联导入记录ID',
    `row_number`        INT DEFAULT NULL COMMENT '原始行号',
    id_card_number      VARCHAR(18) DEFAULT NULL COMMENT '身份证号',
    name                VARCHAR(255) DEFAULT NULL COMMENT '姓名',
    gender              VARCHAR(10) DEFAULT NULL COMMENT '性别',
    age                 VARCHAR(10) DEFAULT NULL COMMENT '年龄',
    address             VARCHAR(500) DEFAULT NULL COMMENT '住址',
    contact             VARCHAR(255) DEFAULT NULL COMMENT '联系方式',
    is_valid            TINYINT DEFAULT 1 COMMENT '校验是否通过: 0否 1是',
    validation_error    VARCHAR(500) DEFAULT NULL COMMENT '校验错误信息',
    is_duplicate        TINYINT DEFAULT 0 COMMENT '是否与已有数据重复: 0否 1是',
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_import_log_id (import_log_id),
    INDEX idx_id_card_number (id_card_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='人口数据导入暂存表';


-- ==================== 案件数据导入暂存表 ====================
CREATE TABLE IF NOT EXISTS case_staging (
    id                  INT AUTO_INCREMENT PRIMARY KEY COMMENT 'ID',
    import_log_id       INT DEFAULT NULL COMMENT '关联导入记录ID',
    `row_number`        INT DEFAULT NULL COMMENT '原始行号',
    case_number         VARCHAR(100) DEFAULT NULL COMMENT '案件编号',
    case_name           VARCHAR(500) DEFAULT NULL COMMENT '案件名称',
    case_type           VARCHAR(100) DEFAULT NULL COMMENT '案件类型',
    incident_time_str   VARCHAR(50) DEFAULT NULL COMMENT '案发时间(原始字符串)',
    incident_location   VARCHAR(500) DEFAULT NULL COMMENT '案发地点',
    involved_persons    TEXT DEFAULT NULL COMMENT '涉案人员(原始文本,逗号分隔)',
    is_valid            TINYINT DEFAULT 1 COMMENT '校验是否通过: 0否 1是',
    validation_error    VARCHAR(500) DEFAULT NULL COMMENT '校验错误信息',
    is_duplicate        TINYINT DEFAULT 0 COMMENT '是否与已有数据重复: 0否 1是',
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_import_log_id (import_log_id),
    INDEX idx_case_number (case_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='案件数据导入暂存表';


-- ==================== 布控人员表增加数据来源字段 ====================
ALTER TABLE young_peoples
    ADD COLUMN IF NOT EXISTS data_source VARCHAR(50) DEFAULT 'manual' COMMENT '数据来源: manual/jingzong/renkou/other',
    ADD COLUMN IF NOT EXISTS source_import_log_id INT DEFAULT NULL COMMENT '来源导入记录ID';
