package com.biopolymer.screening.data.remote

import com.biopolymer.screening.data.remote.dto.HealthResponseDto
import com.biopolymer.screening.data.remote.dto.ScreeningRequestDto
import com.biopolymer.screening.data.remote.dto.ScreeningResponseDto
import retrofit2.Response
import retrofit2.http.*

/**
 * Retrofit API interface — REST endpoints served by the FastAPI backend.
 */
interface ApiService {


    // ------------------------------------------------------------------
    // AI Screening (Primary REST Endpoint)
    // ------------------------------------------------------------------

    @POST("api/v1/screening")
    suspend fun screenMaterials(
        @Body request: ScreeningRequestDto
    ): Response<ScreeningResponseDto>

    @POST("api/v1/screening/explain")
    suspend fun getExplanation(
        @Body request: Map<String, Any?>
    ): Response<Map<String, Any?>>

    // ------------------------------------------------------------------
    // Materials Catalog — paginated browsing (UI browsing, search)
    // ------------------------------------------------------------------

    @GET("api/v1/materials")
    suspend fun getMaterials(
        @Query("category") category: String? = null,
        @Query("search") search: String? = null,
        @Query("skip") skip: Int = 0,
        @Query("limit") limit: Int = 50,
    ): Response<List<Map<String, Any?>>>

    @GET("api/v1/materials/categories")
    suspend fun getCategories(): Response<List<String>>

    @GET("api/v1/materials/properties")
    suspend fun getPropertySchema(): Response<Map<String, Any?>>

    @GET("api/v1/materials/{materialId}")
    suspend fun getMaterial(
        @Path("materialId") materialId: String,
    ): Response<Map<String, Any?>>

    // ------------------------------------------------------------------
    // Model Metadata & System Statistics
    // ------------------------------------------------------------------

    @GET("api/v1/model/info")
    suspend fun getModelInfo(): Response<Map<String, Any?>>

    @GET("api/v1/statistics")
    suspend fun getStatistics(): Response<Map<String, Any?>>

    // ------------------------------------------------------------------
    // Projects
    // ------------------------------------------------------------------

    @GET("api/v1/projects")
    suspend fun getProjects(): Response<List<Map<String, Any?>>>

    @POST("api/v1/projects")
    suspend fun createProject(
        @Body project: Map<String, Any?>,
    ): Response<Map<String, Any?>>

    @PUT("api/v1/projects/{projectId}")
    suspend fun updateProject(
        @Path("projectId") projectId: String,
        @Body project: Map<String, Any?>,
    ): Response<Map<String, Any?>>

    @DELETE("api/v1/projects/{projectId}")
    suspend fun deleteProject(
        @Path("projectId") projectId: String,
    ): Response<Unit>

    // ------------------------------------------------------------------
    // Operational Health
    // ------------------------------------------------------------------

    @GET("health")
    suspend fun healthCheck(): Response<HealthResponseDto>
}
