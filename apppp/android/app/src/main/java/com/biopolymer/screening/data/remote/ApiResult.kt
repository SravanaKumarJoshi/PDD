package com.biopolymer.screening.data.remote

/**
 * A discriminated union that wraps every API call result.
 *
 * Use this as the return type of every repository function that performs
 * a network operation.  ViewModels map [ApiResult] to UI state without
 * ever catching raw exceptions.
 *
 * ```kotlin
 * // Repository
 * suspend fun getMaterials(): ApiResult<List<Material>> = safeApiCall {
 *     apiService.getMaterials()
 * }
 *
 * // ViewModel
 * when (val result = repository.getMaterials()) {
 *     is ApiResult.Success -> uiState = MaterialsLoaded(result.data)
 *     is ApiResult.Error   -> uiState = Error(result.exception.userMessage)
 *     is ApiResult.Loading -> uiState = Loading
 * }
 * ```
 */
sealed class ApiResult<out T> {

    /** The operation completed successfully and [data] is available. */
    data class Success<T>(val data: T) : ApiResult<T>()

    /**
     * The operation failed with a typed [NetworkException].
     * The exception carries a safe [NetworkException.userMessage] string.
     */
    data class Error(val exception: NetworkException) : ApiResult<Nothing>()

    /** An in-flight operation.  Emitted by StateFlow / LiveData sources. */
    data object Loading : ApiResult<Nothing>()

    // ------------------------------------------------------------------
    // Convenience helpers
    // ------------------------------------------------------------------

    val isSuccess: Boolean get() = this is Success
    val isError: Boolean get() = this is Error
    val isLoading: Boolean get() = this is Loading

    /** Returns the data if [Success], null otherwise. */
    fun getOrNull(): T? = (this as? Success)?.data

    /** Returns the exception if [Error], null otherwise. */
    fun errorOrNull(): NetworkException? = (this as? Error)?.exception

    /**
     * Maps [Success] data to a new type while leaving [Error] and [Loading]
     * untouched.  Useful for transforming domain models in repositories.
     */
    fun <R> map(transform: (T) -> R): ApiResult<R> = when (this) {
        is Success -> Success(transform(data))
        is Error   -> this
        is Loading -> this
    }

    /**
     * Executes [onSuccess] if this is [Success].
     * Returns `this` for chaining.
     */
    inline fun onSuccess(action: (T) -> Unit): ApiResult<T> {
        if (this is Success) action(data)
        return this
    }

    /**
     * Executes [onError] if this is [Error].
     * Returns `this` for chaining.
     */
    inline fun onError(action: (NetworkException) -> Unit): ApiResult<T> {
        if (this is Error) action(exception)
        return this
    }
}
