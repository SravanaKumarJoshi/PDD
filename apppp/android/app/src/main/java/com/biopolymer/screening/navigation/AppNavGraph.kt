package com.biopolymer.screening.navigation

import androidx.compose.animation.*
import androidx.compose.animation.core.tween
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.compose.*
import com.biopolymer.screening.ui.catalog.CatalogScreen
import com.biopolymer.screening.ui.catalog.MaterialDetailScreen
import com.biopolymer.screening.ui.onboarding.OnboardingScreen
import com.biopolymer.screening.ui.requirements.RequirementsEvent
import com.biopolymer.screening.ui.requirements.RequirementsScreen
import com.biopolymer.screening.ui.requirements.RequirementsViewModel
import com.biopolymer.screening.ui.results.ResultsScreen
import com.biopolymer.screening.ui.projects.ProjectsScreen
import com.biopolymer.screening.ui.settings.SettingsScreen

sealed class Screen(val route: String, val label: String, val icon: ImageVector, val selectedIcon: ImageVector) {
    data object Home : Screen("home_root", "Screen", Icons.Outlined.Science, Icons.Filled.Science)
    data object Catalog : Screen("catalog", "Catalog", Icons.Outlined.Inventory2, Icons.Filled.Inventory2)
    data object Projects : Screen("projects", "Projects", Icons.Outlined.FolderOpen, Icons.Filled.Folder)
    data object Settings : Screen("settings", "Settings", Icons.Outlined.Settings, Icons.Filled.Settings)
}

val bottomNavScreens = listOf(Screen.Home, Screen.Catalog, Screen.Projects, Screen.Settings)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AppNavGraph() {
    val navController = rememberNavController()
    val navBackStackEntry by navController.currentBackStackEntryAsState()
    val currentRoute = navBackStackEntry?.destination?.route

    // Track whether onboarding has been shown
    var showOnboarding by remember { mutableStateOf(true) }

    val showBottomBar = currentRoute in bottomNavScreens.map { it.route } || 
                      currentRoute == "home" || currentRoute == "results"

    Scaffold(
        bottomBar = {
            if (showBottomBar) {
                NavigationBar(
                    tonalElevation = 0.dp // Modern flat look
                ) {
                    bottomNavScreens.forEach { screen ->
                        val selected = currentRoute == screen.route || 
                                     (screen == Screen.Home && (currentRoute == "home" || currentRoute == "results"))
                        NavigationBarItem(
                            selected = selected,
                            onClick = {
                                navController.navigate(screen.route) {
                                    popUpTo(navController.graph.findStartDestination().id) {
                                        saveState = true
                                    }
                                    launchSingleTop = true
                                    restoreState = true
                                }
                            },
                            icon = {
                                Icon(
                                    imageVector = if (selected) screen.selectedIcon else screen.icon,
                                    contentDescription = screen.label
                                )
                            },
                            label = { Text(screen.label) }
                        )
                    }
                }
            }
        }
    ) { innerPadding ->
        NavHost(
            navController = navController,
            startDestination = if (showOnboarding) "onboarding" else Screen.Home.route,
            modifier = Modifier.padding(bottom = innerPadding.calculateBottomPadding()),
            enterTransition = {
                fadeIn(animationSpec = tween(300)) + slideIntoContainer(
                    AnimatedContentTransitionScope.SlideDirection.Start,
                    animationSpec = tween(300)
                )
            },
            exitTransition = {
                fadeOut(animationSpec = tween(300)) + slideOutOfContainer(
                    AnimatedContentTransitionScope.SlideDirection.Start,
                    animationSpec = tween(300)
                )
            },
            popEnterTransition = {
                fadeIn(animationSpec = tween(300)) + slideIntoContainer(
                    AnimatedContentTransitionScope.SlideDirection.End,
                    animationSpec = tween(300)
                )
            },
            popExitTransition = {
                fadeOut(animationSpec = tween(300)) + slideOutOfContainer(
                    AnimatedContentTransitionScope.SlideDirection.End,
                    animationSpec = tween(300)
                )
            }
        ) {
            composable("onboarding") {
                OnboardingScreen(
                    onComplete = {
                        navController.navigate(Screen.Home.route) {
                            popUpTo("onboarding") { inclusive = true }
                        }
                    }
                )
            }

            navigation(startDestination = "home", route = Screen.Home.route) {
                composable("home") { backStackEntry ->
                    val parentEntry = remember(backStackEntry) {
                        navController.getBackStackEntry(Screen.Home.route)
                    }
                    val viewModel: RequirementsViewModel = hiltViewModel(parentEntry)
                    RequirementsScreen(
                        onViewResults = { navController.navigate("results") { launchSingleTop = true } },
                        viewModel = viewModel
                    )
                }

                composable("results") { backStackEntry ->
                    val parentEntry = remember(backStackEntry) {
                        navController.getBackStackEntry(Screen.Home.route)
                    }
                    val viewModel: RequirementsViewModel = hiltViewModel(parentEntry)
                    ResultsScreen(
                        onNavigateBack = { navController.popBackStack() },
                        onMaterialDetail = { id -> navController.navigate("material/$id") },
                        onNavigateHome = {
                            viewModel.relaxConstraints()
                            navController.navigate("home") {
                                popUpTo(navController.graph.findStartDestination().id)
                                launchSingleTop = true
                            }
                        },
                        viewModel = viewModel
                    )
                }
            }

            composable(Screen.Catalog.route) {
                CatalogScreen(
                    onMaterialClick = { id -> navController.navigate("material/$id") }
                )
            }

            composable("material/{materialId}") { backStackEntry ->
                val materialId = backStackEntry.arguments?.getString("materialId") ?: ""
                MaterialDetailScreen(
                    materialId = materialId,
                    onNavigateBack = { navController.popBackStack() }
                )
            }

            composable(Screen.Projects.route) {
                val homeEntry = remember(it) { navController.getBackStackEntry(Screen.Home.route) }
                val requirementsViewModel: RequirementsViewModel = hiltViewModel(homeEntry)
                
                // Listen to navigation events
                LaunchedEffect(Unit) {
                    requirementsViewModel.events.collect { event ->
                        when (event) {
                            is RequirementsEvent.NavigateToResults -> {
                                navController.navigate("results") { launchSingleTop = true }
                            }
                        }
                    }
                }
                
                ProjectsScreen(
                    onScreeningClick = { screening ->
                        requirementsViewModel.loadSavedScreening(screening)
                        navController.navigate("results") { launchSingleTop = true }
                    }
                )
            }

            composable(Screen.Settings.route) {
                SettingsScreen()
            }
        }
    }
}
