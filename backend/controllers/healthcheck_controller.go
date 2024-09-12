package controllers

import (
	"net/http"
	"fmt"
	"gorm.io/gorm"
)

func HealthCHeck(db *gorm.DB) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {

		sqlDB, err := db.DB()
		if err != nil {
			http.Error(w, "Could not retrieve database object", http.StatusInternalServerError)
			return
		}
	
		err = sqlDB.Ping()
		if err != nil {
			http.Error(w, "Database is not reachable", http.StatusInternalServerError)
			return
		}
	
		fmt.Fprintln(w, "Database is healthy")
	}
}
