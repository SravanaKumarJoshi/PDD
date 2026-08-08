package com.biopolymer.screening.di

import com.biopolymer.screening.data.repository.SavedScreeningRepository
import com.biopolymer.screening.data.repository.SavedScreeningRepositoryImpl
import dagger.Binds
import dagger.Module
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
abstract class RepositoryModule {

    @Binds
    @Singleton
    abstract fun bindSavedScreeningRepository(
        impl: SavedScreeningRepositoryImpl
    ): SavedScreeningRepository
}
