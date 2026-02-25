package com.hayatinritmi.app.domain.model

data class AiPrediction(
    val label: ArrhythmiaClass = ArrhythmiaClass.UNKNOWN,
    val confidence: Float = 0f,
    val probabilities: FloatArray = FloatArray(55),
    val topPredictions: List<Pair<String, Float>> = emptyList(),
    val rrIrregularityScore: Float = 0f,
    val inferenceTimeMs: Long = 0L,
    val windowTimestampMs: Long = 0L
) {
    val isLowConfidence: Boolean get() = confidence < 0.55f
    val needsRecheck: Boolean get() = confidence in 0.55f..0.80f
    val isHighConfidence: Boolean get() = confidence >= 0.80f

    override fun equals(other: Any?): Boolean {
        if (this === other) return true
        if (other !is AiPrediction) return false
        return label == other.label &&
            confidence == other.confidence &&
            probabilities.contentEquals(other.probabilities) &&
            topPredictions == other.topPredictions &&
            rrIrregularityScore == other.rrIrregularityScore &&
            inferenceTimeMs == other.inferenceTimeMs &&
            windowTimestampMs == other.windowTimestampMs
    }

    override fun hashCode(): Int {
        var result = label.hashCode()
        result = 31 * result + confidence.hashCode()
        result = 31 * result + probabilities.contentHashCode()
        result = 31 * result + topPredictions.hashCode()
        result = 31 * result + rrIrregularityScore.hashCode()
        result = 31 * result + inferenceTimeMs.hashCode()
        result = 31 * result + windowTimestampMs.hashCode()
        return result
    }
}
