-- Sugar Plant Predictive Maintenance System
-- MySQL / MariaDB Schema

CREATE DATABASE IF NOT EXISTS `sugar_plant_maintenance`
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE `sugar_plant_maintenance`;

-- 1. Users table (RBAC)
CREATE TABLE IF NOT EXISTS `users` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `username` VARCHAR(80) NOT NULL UNIQUE,
  `email` VARCHAR(120) NOT NULL UNIQUE,
  `password_hash` VARCHAR(255) NOT NULL,
  `role` VARCHAR(30) NOT NULL DEFAULT 'technician',
  `full_name` VARCHAR(120) NULL,
  `is_active` BOOLEAN NOT NULL DEFAULT TRUE,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX `idx_users_role` (`role`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. Plant Areas table
CREATE TABLE IF NOT EXISTS `plant_areas` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `name` VARCHAR(120) NOT NULL UNIQUE,
  `code` VARCHAR(50) NOT NULL UNIQUE,
  `description` TEXT NULL,
  `is_active` BOOLEAN NOT NULL DEFAULT TRUE,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. Equipment table
CREATE TABLE IF NOT EXISTS `equipment` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `equipment_tag` VARCHAR(50) NOT NULL UNIQUE,
  `name` VARCHAR(120) NOT NULL,
  `equipment_type` VARCHAR(80) NOT NULL,
  `plant_area_id` INT NOT NULL,
  `description` TEXT NULL,
  `operating_status` VARCHAR(30) NOT NULL DEFAULT 'running',
  `installation_date` DATE NULL,
  `maintenance_info` TEXT NULL,
  `is_active` BOOLEAN NOT NULL DEFAULT TRUE,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT `fk_equipment_plant_area` FOREIGN KEY (`plant_area_id`) REFERENCES `plant_areas` (`id`) ON DELETE RESTRICT,
  INDEX `idx_equipment_status` (`operating_status`),
  INDEX `idx_equipment_type` (`equipment_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. Sensor Definitions (Configurable thresholds)
CREATE TABLE IF NOT EXISTS `sensor_definitions` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `equipment_id` INT NOT NULL,
  `sensor_type` VARCHAR(50) NOT NULL,
  `sensor_name` VARCHAR(100) NOT NULL,
  `unit` VARCHAR(20) NOT NULL,
  `min_acceptable` FLOAT NOT NULL DEFAULT 0.0,
  `max_acceptable` FLOAT NOT NULL DEFAULT 100.0,
  `warning_min` FLOAT NULL,
  `warning_max` FLOAT NULL,
  `critical_min` FLOAT NULL,
  `critical_max` FLOAT NULL,
  `is_enabled` BOOLEAN NOT NULL DEFAULT TRUE,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT `fk_sensors_equipment` FOREIGN KEY (`equipment_id`) REFERENCES `equipment` (`id`) ON DELETE CASCADE,
  INDEX `idx_sensor_type` (`sensor_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 5. Simulation Runs
CREATE TABLE IF NOT EXISTS `simulation_runs` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `name` VARCHAR(120) NOT NULL,
  `scenario` VARCHAR(80) NOT NULL DEFAULT 'normal',
  `status` VARCHAR(30) NOT NULL DEFAULT 'stopped',
  `speed_factor` FLOAT NOT NULL DEFAULT 1.0,
  `selected_equipment_id` INT NULL,
  `started_at` DATETIME NULL,
  `ended_at` DATETIME NULL,
  `created_by_id` INT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT `fk_sim_equipment` FOREIGN KEY (`selected_equipment_id`) REFERENCES `equipment` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_sim_user` FOREIGN KEY (`created_by_id`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 6. Sensor Readings (Simulated factory telemetry)
CREATE TABLE IF NOT EXISTS `sensor_readings` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `equipment_id` INT NOT NULL,
  `sensor_definition_id` INT NOT NULL,
  `simulation_run_id` INT NULL,
  `sensor_type` VARCHAR(50) NOT NULL,
  `value` FLOAT NOT NULL,
  `unit` VARCHAR(20) NOT NULL,
  `status` VARCHAR(20) NOT NULL DEFAULT 'normal',
  `is_simulated` BOOLEAN NOT NULL DEFAULT TRUE,
  `recorded_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT `fk_readings_equipment` FOREIGN KEY (`equipment_id`) REFERENCES `equipment` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_readings_sensor_def` FOREIGN KEY (`sensor_definition_id`) REFERENCES `sensor_definitions` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_readings_simulation_run` FOREIGN KEY (`simulation_run_id`) REFERENCES `simulation_runs` (`id`) ON DELETE SET NULL,
  INDEX `idx_readings_time` (`recorded_at`),
  INDEX `idx_readings_sensor_type` (`sensor_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 7. Fault Alerts
CREATE TABLE IF NOT EXISTS `fault_alerts` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `equipment_id` INT NOT NULL,
  `sensor_definition_id` INT NULL,
  `simulation_run_id` INT NULL,
  `sensor_type` VARCHAR(50) NOT NULL,
  `observed_value` FLOAT NOT NULL,
  `configured_limit` FLOAT NOT NULL,
  `severity` VARCHAR(20) NOT NULL DEFAULT 'warning',
  `description` TEXT NOT NULL,
  `status` VARCHAR(20) NOT NULL DEFAULT 'active',
  `acknowledged_by_id` INT NULL,
  `acknowledged_at` DATETIME NULL,
  `resolved_by_id` INT NULL,
  `resolved_at` DATETIME NULL,
  `comments` TEXT NULL,
  `last_occurred_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT `fk_alerts_equipment` FOREIGN KEY (`equipment_id`) REFERENCES `equipment` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_alerts_sensor_def` FOREIGN KEY (`sensor_definition_id`) REFERENCES `sensor_definitions` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_alerts_ack_user` FOREIGN KEY (`acknowledged_by_id`) REFERENCES `users` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_alerts_res_user` FOREIGN KEY (`resolved_by_id`) REFERENCES `users` (`id`) ON DELETE SET NULL,
  INDEX `idx_alerts_status` (`status`),
  INDEX `idx_alerts_severity` (`severity`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 8. Machine Learning Failure Predictions
CREATE TABLE IF NOT EXISTS `failure_predictions` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `equipment_id` INT NOT NULL,
  `risk_category` VARCHAR(20) NOT NULL DEFAULT 'low',
  `risk_score` FLOAT NOT NULL,
  `contributing_factors` TEXT NULL,
  `recommended_action` TEXT NOT NULL,
  `model_version` VARCHAR(50) NOT NULL DEFAULT 'RandomForest-v1.0',
  `is_simulated` BOOLEAN NOT NULL DEFAULT TRUE,
  `prediction_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT `fk_pred_equipment` FOREIGN KEY (`equipment_id`) REFERENCES `equipment` (`id`) ON DELETE CASCADE,
  INDEX `idx_pred_risk` (`risk_category`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 9. Work Orders
CREATE TABLE IF NOT EXISTS `work_orders` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `work_order_number` VARCHAR(50) NOT NULL UNIQUE,
  `equipment_id` INT NOT NULL,
  `alert_id` INT NULL,
  `title` VARCHAR(150) NOT NULL,
  `problem_description` TEXT NOT NULL,
  `priority` VARCHAR(20) NOT NULL DEFAULT 'medium',
  `status` VARCHAR(30) NOT NULL DEFAULT 'open',
  `due_date` DATE NULL,
  `assigned_to_id` INT NULL,
  `created_by_id` INT NOT NULL,
  `inspection_findings` TEXT NULL,
  `repair_actions` TEXT NULL,
  `parts_used` TEXT NULL,
  `labor_hours` FLOAT NOT NULL DEFAULT 0.0,
  `maintenance_cost` FLOAT NOT NULL DEFAULT 0.0,
  `completion_reason` TEXT NULL,
  `completed_at` DATETIME NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT `fk_wo_equipment` FOREIGN KEY (`equipment_id`) REFERENCES `equipment` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_wo_alert` FOREIGN KEY (`alert_id`) REFERENCES `fault_alerts` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_wo_assignee` FOREIGN KEY (`assigned_to_id`) REFERENCES `users` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_wo_creator` FOREIGN KEY (`created_by_id`) REFERENCES `users` (`id`) ON DELETE RESTRICT,
  INDEX `idx_wo_status` (`status`),
  INDEX `idx_wo_priority` (`priority`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 10. Maintenance Records (Equipment repair & service history)
CREATE TABLE IF NOT EXISTS `maintenance_records` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `equipment_id` INT NOT NULL,
  `work_order_id` INT NULL,
  `record_type` VARCHAR(50) NOT NULL DEFAULT 'corrective',
  `title` VARCHAR(150) NOT NULL,
  `description` TEXT NOT NULL,
  `action_taken` TEXT NOT NULL,
  `parts_replaced` TEXT NULL,
  `labor_hours` FLOAT NOT NULL DEFAULT 0.0,
  `cost` FLOAT NOT NULL DEFAULT 0.0,
  `estimated_downtime_hours` FLOAT NOT NULL DEFAULT 0.0,
  `performed_by_id` INT NULL,
  `performed_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT `fk_maint_rec_equipment` FOREIGN KEY (`equipment_id`) REFERENCES `equipment` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_maint_rec_wo` FOREIGN KEY (`work_order_id`) REFERENCES `work_orders` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_maint_rec_user` FOREIGN KEY (`performed_by_id`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 11. Maintenance Schedules (Preventive maintenance)
CREATE TABLE IF NOT EXISTS `maintenance_schedules` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `equipment_id` INT NOT NULL,
  `title` VARCHAR(150) NOT NULL,
  `description` TEXT NULL,
  `interval_days` INT NOT NULL,
  `last_performed_at` DATETIME NULL,
  `next_due_date` DATE NOT NULL,
  `assigned_to_id` INT NULL,
  `is_active` BOOLEAN NOT NULL DEFAULT TRUE,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT `fk_sched_equipment` FOREIGN KEY (`equipment_id`) REFERENCES `equipment` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_sched_assignee` FOREIGN KEY (`assigned_to_id`) REFERENCES `users` (`id`) ON DELETE SET NULL,
  INDEX `idx_sched_due` (`next_due_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 12. Audit Logs
CREATE TABLE IF NOT EXISTS `audit_logs` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `user_id` INT NULL,
  `action` VARCHAR(100) NOT NULL,
  `entity_type` VARCHAR(50) NOT NULL,
  `entity_id` INT NULL,
  `details` TEXT NULL,
  `ip_address` VARCHAR(45) NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT `fk_audit_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL,
  INDEX `idx_audit_created` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
