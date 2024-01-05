package main

import (
	"fmt"
	"net/http"
)

func main() {
	handler := func(w http.ResponseWriter, r *http.Request) {
		fmt.Fprintf(w, "test reply")
	}
	http.HandleFunc("/", handler)
	port := 8089
	fmt.Printf("Host :%d...\n", port)
	err := http.ListenAndServe(fmt.Sprintf(":%d", port), nil)
	if err != nil {
		fmt.Printf("err %s\n", err)
	}
}
