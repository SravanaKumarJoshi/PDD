package com.biopolymer.screening.di

import android.content.Context
import androidx.room.Room
import com.biopolymer.screening.data.local.AppDatabase
import com.biopolymer.screening.data.local.AppDatabase.Companion.MIGRATION_1_2
import com.biopolymer.screening.data.local.AppDatabase.Companion.MIGRATION_2_3
import com.biopolymer.screening.data.local.AppDatabase.Companion.MIGRATION_3_4
import com.biopolymer.screening.data.local.AppDatabase.Companion.MIGRATION_4_5
import com.biopolymer.screening.data.local.AppDatabase.Companion.MIGRATION_5_6
import com.biopolymer.screening.data.local.AppDatabase.Companion.MIGRATION_6_7
import com.biopolymer.screening.data.local.dao.MaterialDao
import com.biopolymer.screening.data.local.dao.ProjectDao
import com.biopolymer.screening.data.local.dao.SavedScreeningDao
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

/**
 * Provides the Room database and its DAOs for local storage and offline catalogue browsing.
 */
@Module
@InstallIn(SingletonComponent::class)
object DatabaseModule {

    @Provides
    @Singleton
    fun provideDatabase(@ApplicationContext context: Context): AppDatabase =
        Room.databaseBuilder(context, AppDatabase::class.java, AppDatabase.DATABASE_NAME)
            .addMigrations(MIGRATION_1_2, MIGRATION_2_3, MIGRATION_3_4, MIGRATION_4_5, MIGRATION_5_6, MIGRATION_6_7)
            .fallbackToDestructiveMigrationOnDowngrade()
            .build()

    @Provides
    fun provideMaterialDao(db: AppDatabase): MaterialDao = db.materialDao()

    @Provides
    fun provideProjectDao(db: AppDatabase): ProjectDao = db.projectDao()

    @Provides
    fun provideSavedScreeningDao(db: AppDatabase): SavedScreeningDao = db.savedScreeningDao()

    @Provides
    @Singleton
    fun provideScoringEngine(): com.biopolymer.screening.domain.scoring.ScoringEngine =
        com.biopolymer.screening.domain.scoring.ScoringEngine()
}

