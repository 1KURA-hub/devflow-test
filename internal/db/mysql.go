package db

import (
	"time"

	"devflow/internal/config"
	"devflow/internal/model"

	"gorm.io/driver/mysql"
	"gorm.io/gorm"
)

func Open(cfg config.Config) (*gorm.DB, error) {
	database, err := gorm.Open(mysql.Open(cfg.MySQLDSN), &gorm.Config{})
	if err != nil {
		return nil, err
	}

	sqlDB, err := database.DB()
	if err != nil {
		return nil, err
	}
	if err := sqlDB.Ping(); err != nil {
		return nil, err
	}

	// 连接池显式设限。Go 默认 MaxOpenConns 无上限、MaxIdleConns 仅 2，
	// 高并发下会频繁建连/断连并复用已被服务端关闭的连接，
	// 压测中表现为 "driver: bad connection"，这里固定上限与生命周期。
	sqlDB.SetMaxOpenConns(50)
	sqlDB.SetMaxIdleConns(25)
	sqlDB.SetConnMaxLifetime(30 * time.Minute)
	sqlDB.SetConnMaxIdleTime(5 * time.Minute)

	if cfg.AutoMigrate {
		if err := database.AutoMigrate(
			&model.User{},
			&model.Post{},
			&model.Follow{},
			&model.Like{},
			&model.Favorite{},
			&model.Comment{},
			&model.Notification{},
			&model.ProcessedEvent{},
		); err != nil {
			return nil, err
		}
	}

	return database, nil
}
