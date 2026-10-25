package api

import (
	"bytes"
	"context"
	"io"
	"net/http"
	"strings"
	"time"
)

const maxPredictBody = 1 << 20 // 1 MiB

// predict forwards a forecast request to the Python inference service (pipeline/serve.py).
// The service validates the data; this handler only bounds size and type and maps outages.
func (s *Server) predict(w http.ResponseWriter, r *http.Request) {
	if s.InferenceURL == "" {
		writeError(w, http.StatusServiceUnavailable, "inference service is not configured (set INFERENCE_URL)")
		return
	}
	if ct := r.Header.Get("Content-Type"); !strings.HasPrefix(ct, "application/json") {
		writeError(w, http.StatusUnsupportedMediaType, "Content-Type must be application/json")
		return
	}
	body, err := io.ReadAll(http.MaxBytesReader(w, r.Body, maxPredictBody))
	if err != nil {
		writeError(w, http.StatusRequestEntityTooLarge, "request body too large or unreadable")
		return
	}
	ctx, cancel := context.WithTimeout(r.Context(), 30*time.Second)
	defer cancel()
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, strings.TrimRight(s.InferenceURL, "/")+"/predict", bytes.NewReader(body))
	if err != nil {
		s.internal(w, err)
		return
	}
	req.Header.Set("Content-Type", "application/json")
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		writeError(w, http.StatusBadGateway, "inference service is unreachable")
		return
	}
	defer resp.Body.Close()
	out, err := io.ReadAll(io.LimitReader(resp.Body, maxPredictBody))
	if err != nil {
		writeError(w, http.StatusBadGateway, "inference service returned an unreadable response")
		return
	}
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(resp.StatusCode)
	_, _ = w.Write(out)
}
