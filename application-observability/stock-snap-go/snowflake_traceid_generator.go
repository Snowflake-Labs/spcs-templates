package main

import (
	"context"
	crand "crypto/rand"
	"encoding/binary"
	"math/rand"
	"sync"
	"time"

	"go.opentelemetry.io/otel/trace"
)

// SnowflakeTraceIdGenerator generates trace IDs incorporating a timestamp component to ensure both uniqueness and traceability.
// Generated trace ID consists of a leading section derived from the timestamp and a trailing section composed of a random suffix.
// Using this generator is required for Snowflake to display traces & spans in Snowsight UI.
type snowflakeTraceIDGenerator struct {
	sync.Mutex
	randSource *rand.Rand
}

func (gen *snowflakeTraceIDGenerator) NewIDs(ctx context.Context) (trace.TraceID, trace.SpanID) {
	gen.Lock()
	defer gen.Unlock()

	tid := trace.TraceID{}
	timestampInMinutes := time.Now().Unix() / 60
	binary.BigEndian.PutUint32(tid[:4], uint32(timestampInMinutes))
	for {
		_, _ = gen.randSource.Read(tid[4:])
		if tid.IsValid() {
			break
		}
	}

	sid := trace.SpanID{}
	for {
		_, _ = gen.randSource.Read(sid[:])
		if sid.IsValid() {
			break
		}
	}

	return tid, sid
}

func (gen *snowflakeTraceIDGenerator) NewSpanID(ctx context.Context, traceID trace.TraceID) trace.SpanID {
	gen.Lock()
	defer gen.Unlock()
	sid := trace.SpanID{}
	for {
		_, _ = gen.randSource.Read(sid[:])
		if sid.IsValid() {
			break
		}
	}
	return sid
}

func newSnowflakeTraceIDGenerator() *snowflakeTraceIDGenerator {
	gen := &snowflakeTraceIDGenerator{}
	var rngSeed int64
	_ = binary.Read(crand.Reader, binary.BigEndian, &rngSeed)
	gen.randSource = rand.New(rand.NewSource(rngSeed))
	return gen
}
