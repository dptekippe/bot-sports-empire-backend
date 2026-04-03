/**
 * OpenRCT2 Plugin: JSON Action Bridge
 * ============================================================================
 * ARCHITECTURE OVERVIEW
 * ============================================================================
 * This plugin implements a TCP-based JSON-RPC bridge that allows external Python clients
 * to control OpenRCT2. The design follows a client-server pattern:
 * 
 *   Python Client (rct2.py)  <--TCP/JSON-->  Bridge Plugin (zmq_bridge.js)  <--API-->  OpenRCT2 Game
 * 
 * DESIGN DECISIONS:
 * 1. TCP Protocol: Uses TCP for reliable, ordered message delivery
 * 2. JSON Format: Human-readable, easy to debug, language-agnostic
 * 3. Newline-delimited: Each JSON message ends with '\n' for simple parsing
 * 4. Two-tier Action System:
 *    - Special Actions: Custom handlers for read-only queries (get_park_info, etc.)
 *    - Game Actions: Direct passthrough to OpenRCT2's context.executeAction()
 * 
 * PROTOCOL:
 * - Request: {"action": "action_name", "param1": value1, ...}\n
 * - Response: {"status": "ok|error", "result": {...} or "error": code, ...}\n
 * 
 * The server listens on localhost:11752 by default.
 * 
 * ============================================================================
 * HOW TO USE:
 * ============================================================================
 * Pre-requisites:
 * 1. OpenRCT2 must be installed and able to run from the command line
 * 2. Node.js and Python must be installed
 * 3. The zmq_bridge.js file must be placed in the OpenRCT2 plugin directory
 *    - macOS: ~/Library/Application Support/OpenRCT2/plugin/
 * 
 * Steps:
 * 1. Start an instance of OpenRCT2 from the command line.
 *    - The plugin will automatically start listening on port 11752 when OpenRCT2 loads.
 * 2. Use the RCTThemePark() class to send JSON messages to the bridge (see rct2.py for examples)
 * 
 * PS. If you modify this file, you must restart OpenRCT2 to reload plugins
 */

registerPlugin({
    // Fields required by OpenRCT2's plugin system
    name: "JSON Action Bridge",
    version: "1.0.0",
    authors: ["Auto-generated"],
    type: "local",
    targetApiVersion: 66,
    main: function() {
        const BRIDGE_PORT = 11752;
        
        console.log("JSON Action Bridge: Starting server on port " + BRIDGE_PORT);
        
        // Pause the game on startup (optional - comment out if not needed)
        // This ensures the game starts paused when using the bridge
        if (!context.paused) {
            context.executeAction("pausetoggle", {});
            console.log("JSON Action Bridge: Game paused on startup");
        }
        
        // Create TCP listener - this is the server socket that accepts connections
        // from Python clients (rct2.py). The plugin runs inside OpenRCT2's JavaScript
        // runtime, so it has direct access to the game's APIs (map, park, context, etc.)
        var server = network.createListener();
        
        server.on('connection', function(conn) {
            console.log("JSON Action Bridge: Client connected from " + conn.remoteAddress);
            
            var buffer = "";
            
            conn.on('data', function(data) {
                try {
                    // PROTOCOL: Newline-delimited JSON messages
                    // Python client sends: '{"action":"ridecreate",...}\n'
                    // We accumulate bytes until we see a newline, then parse the complete JSON
                    // This handles TCP's stream nature where data may arrive in chunks
                    buffer += data.toString();
                    
                    // Split by newlines to get complete messages
                    // Keep the last (potentially incomplete) line in buffer for next data event
                    var lines = buffer.split('\n');
                    buffer = lines.pop() || ""; // Keep incomplete line in buffer
                    
                    // Process each complete JSON message
                    for (var i = 0; i < lines.length; i++) {
                        var line = lines[i].trim();
                        if (line.length === 0) continue;
                        
                        // Handle the message - this is where the action routing happens
                        handleMessage(conn, line);
                    }
                } catch (e) {
                    console.log("JSON Action Bridge: Error handling data: " + e.message);
                    sendResponse(conn, {
                        status: "error",
                        message: e.message
                    });
                }
            });
            
            conn.on('close', function() {
                console.log("JSON Action Bridge: Client disconnected");
            });
            
            conn.on('error', function(err) {
                console.log("JSON Action Bridge: Connection error: " + err);
            });
        });
        
        server.on('error', function(err) {
            console.log("JSON Action Bridge: Server error: " + err);
        });
        
        try {
            server.listen(BRIDGE_PORT);
            console.log("JSON Action Bridge: Server listening on port " + BRIDGE_PORT);
        } catch (e) {
            console.log("JSON Action Bridge: Failed to start server: " + e.message);
        }
        
        /**
         * MESSAGE HANDLING ARCHITECTURE:
         * ==============================
         * This function implements a two-tier action routing system:
         * 
         * 1. SPECIAL ACTIONS (checked first):
         *    - Read-only queries that don't map to game commands
         *    - Examples: get_park_info, get_finance_info, get_guest_info
         *    - These directly access OpenRCT2's scripting API (park, map, date objects)
         *    - Must return early to prevent execution as game action
         * 
         * 2. GAME ACTIONS (fallback):
         *    - All other actions are passed to context.executeAction()
         *    - This is OpenRCT2's standard action execution system
         *    - Examples: ridecreate, trackplace, staffhire, pausetoggle
         * 
         * WHY TWO TIERS?
         * - OpenRCT2's action system is write-only (commands to change game state)
         * - Read operations need direct API access, not actions
         * - Special actions provide a unified interface for both read and write operations
         */
        function handleMessage(conn, jsonStr) {
            try {
                // Parse the JSON message from Python client
                // Format: {"action": "action_name", "param1": value1, ...}
                var msg = JSON.parse(jsonStr);
                var action = msg.action;
                
                if (!action) {
                    sendResponse(conn, {
                        status: "error",
                        message: "Missing 'action' field"
                    });
                    return;
                }
                
                // Extract action arguments - everything except 'action' becomes parameters
                // These will be passed to either special handler or context.executeAction()
                var args = {};
                for (var key in msg) {
                    if (key !== 'action') {
                        args[key] = msg[key];
                    }
                }
                
                if (action !== "get_time_info" && action !== "get_pause_state" && action !== "pausetoggle") {
                    console.log("JSON Action Bridge: Received action: '" + action + "' (type: " + typeof action + ")");
                }
                
// #region Special Actions
                // SPECIAL ACTIONS: Custom handlers for read-only queries
                // These must be checked BEFORE calling context.executeAction because:
                // 1. They don't correspond to game commands
                // 2. They need direct API access (park.cash, map.rides, etc.)
                // 3. They must return early to prevent being executed as a game action
                // 
                // Design pattern: Check special actions first, then fall through to game actions
                var normalizedAction = String(action).trim();
                
                // Special action: Get terrain/surface height at coordinates
                // PURPOSE: Python client needs to know terrain height to place rides/shops at correct Z
                // API ACCESS: Uses map.getTile() to access OpenRCT2's map data directly
                // COORDINATE CONVERSION: Python sends game units (x, y), we convert to tile coords (tileX, tileY)
                //                        Then convert back to game units for height (baseHeight * 8)
                if (normalizedAction === "get_surface_height") {
                    console.log("JSON Action Bridge: Handling get_surface_height query");
                    try {
                        if (msg.x === undefined || msg.y === undefined) {
                            sendResponse(conn, {
                                status: "error",
                                error: 1,
                                errorTitle: "Invalid parameters",
                                errorMessage: "Missing 'x' or 'y' parameter (tile coordinates)"
                            });
                            return;
                        }
                        
                        var tile = map.getTile(msg.x, msg.y);
                        if (!tile) {
                            sendResponse(conn, {
                                status: "error",
                                error: 1,
                                errorTitle: "Can't get surface height",
                                errorMessage: "Invalid tile coordinates"
                            });
                            return;
                        }
                        
                        // Find the surface element in the tile's element stack
                        // Tiles can have multiple elements (surface, track, scenery, etc.)
                        var surfaceHeight = 0;
                        var waterHeight = 0;
                        for (var i = 0; i < tile.numElements; i++) {
                            var element = tile.getElement(i);
                            if (element.type === "surface") {
                                // Convert from tile height units to game units
                                // OpenRCT2 stores height in 1/8th game unit increments
                                surfaceHeight = element.baseHeight * 8;
                                waterHeight = element.waterHeight * 8;
                                break;
                            }
                        }
                        
                        // Send response back to Python client
                        sendResponse(conn, {
                            status: "ok",
                            result: {
                                error: 0,
                                cost: 0,
                                surfaceHeight: surfaceHeight,
                                waterHeight: waterHeight
                            }
                        });
                        return; // CRITICAL: Return early to prevent execution as game action
                    } catch (e) {
                        console.log("JSON Action Bridge: Error getting surface height: " + e.message);
                        sendResponse(conn, {
                            status: "error",
                            message: "Failed to get surface height: " + e.message
                        });
                        return;
                    }
                }

                // Special action: Check if area is owned by park
                // PURPOSE: Python client needs to check if a rectangular area is owned by the park
                // API ACCESS: Uses map.getTile() to access OpenRCT2's map data directly
                // COORDINATE CONVERSION: Python sends tile coordinates (x1, y1, x2, y2)
                // LOGIC: Iterates through all tiles in the area and checks if each surface element has ownership
                if (normalizedAction === "check_area_owned") {
                    console.log("JSON Action Bridge: Handling check_area_owned query");
                    try {
                        if (msg.x1 === undefined || msg.y1 === undefined || msg.x2 === undefined || msg.y2 === undefined) {
                            sendResponse(conn, {
                                status: "error",
                                error: 1,
                                errorTitle: "Invalid parameters",
                                errorMessage: "Missing 'x1', 'y1', 'x2', or 'y2' parameter (tile coordinates)"
                            });
                            return;
                        }
                        
                        var x1 = parseInt(msg.x1);
                        var y1 = parseInt(msg.y1);
                        var x2 = parseInt(msg.x2);
                        var y2 = parseInt(msg.y2);
                        
                        // Ensure x1 <= x2 and y1 <= y2
                        if (x1 > x2) {
                            var temp = x1;
                            x1 = x2;
                            x2 = temp;
                        }
                        if (y1 > y2) {
                            var temp = y1;
                            y1 = y2;
                            y2 = temp;
                        }
                        
                        var allOwned = true;
                        var checkedTiles = 0;
                        var ownedTiles = 0;
                        var ownedTilesArray = [];
                        
                        // Iterate through all tiles in the area
                        for (var x = x1; x <= x2; x++) {
                            for (var y = y1; y <= y2; y++) {
                                var tile = map.getTile(x, y);
                                if (!tile) {
                                    // Invalid tile - consider as not owned
                                    allOwned = false;
                                    checkedTiles++;
                                    continue;
                                }
                                
                                // Find the surface element in the tile's element stack
                                var tileOwned = false;
                                for (var i = 0; i < tile.numElements; i++) {
                                    var element = tile.getElement(i);
                                    if (element.type === "surface") {
                                        // Check if the surface element has ownership
                                        if (element.hasOwnership === true) {
                                            tileOwned = true;
                                            ownedTiles++;
                                            ownedTilesArray.push({
                                                x: x,
                                                y: y,
                                            });
                                        }
                                        break;
                                    }
                                }
                                
                                if (!tileOwned) {
                                    allOwned = false;
                                }
                                checkedTiles++;
                            }
                        }
                        
                        // Send response back to Python client
                        sendResponse(conn, {
                            status: "ok",
                            result: {
                                // error: 0,
                                // cost: 0,
                                allOwned: allOwned,
                                ownedTiles: ownedTilesArray,
                                totalTiles: checkedTiles,
                                area: {
                                    x1: x1,
                                    y1: y1,
                                    x2: x2,
                                    y2: y2
                                }
                            }
                        });
                        return; // CRITICAL: Return early to prevent execution as game action
                    } catch (e) {
                        console.log("JSON Action Bridge: Error checking area ownership: " + e.message);
                        sendResponse(conn, {
                            status: "error",
                            message: "Failed to check area ownership: " + e.message
                        });
                        return;
                    }
                }

                // Special action: Get all rides
                // PURPOSE: Python client needs to query existing rides (read-only operation)
                // API ACCESS: Uses map.rides array from OpenRCT2's scripting API
                // DATA TRANSFORMATION: Converts OpenRCT2's ride objects to JSON-serializable format
                //                      Maps camelCase properties to snake_case for Python convention
                if (normalizedAction === "get_ride_info") {
                    console.log("JSON Action Bridge: Handling get_rides query (special action)");
                    try {
                        // Check API availability - map object is provided by OpenRCT2's scripting runtime
                        if (typeof map === 'undefined') {
                            console.log("JSON Action Bridge: Map API is undefined");
                            sendResponse(conn, {
                                status: "error",
                                error: 1,
                                errorTitle: "Map not available",
                                errorMessage: "Map not available"
                            });
                            return;
                        }
                        // Access all rides in the park - this is a read-only operation
                        var rides = map.rides;
                        if (!rides) {
                            // console.log("JSON Action Bridge: map.rides is null/undefined");
                            sendResponse(conn, {
                                status: "ok",
                                result: {
                                    error: 0,
                                    cost: 0,
                                    rides: []
                                }
                            });
                            return;
                        }
                        // Transform each ride object to a serializable format
                        // OpenRCT2's ride objects have many properties - we extract the relevant ones
                        var rideData = [];
                        for (var i = 0; i < rides.length; i++) {
                            console.log("JSON Action Bridge: Processing ride " + i);
                            var ride = rides[i];
                            var station = (ride.stations && ride.stations.length > 0) ? ride.stations[0] : null;
                            
                            // Helper function to extract coordinates from a location object
                            var extractCoords = function(loc, isRideItself) {
                                isRideItself = isRideItself !== undefined ? isRideItself : false;
                                if (isRideItself) {
                                    return loc ? {
                                        x: loc.x || null,
                                        y: loc.y || null,
                                        z: loc.z || null
                                    } : null;
                                }
                                return loc ? {
                                    x: loc.x || null,
                                    y: loc.y || null,
                                    z: loc.z || null,
                                    direction: loc.direction !== undefined ? loc.direction : null
                                } : null;
                            };
                            
                            var rideInfo = {
                                id: ride.id,
                                type: ride.type || 0,
                                classification: ride.classification || "",
                                status: ride.status || "",
                                excitement: ride.excitement || 0,
                                intensity: ride.intensity || 0,
                                nausea: ride.nausea || 0,
                                value: ride.value || 0,
                                start: station ? extractCoords(station.start, true) : null,
                                entrance: station ? extractCoords(station.entrance) : null,
                                exit: station ? extractCoords(station.exit) : null,
                                prices: (ride.price && ride.price.length > 0) ? ride.price : null,
                                broken: (ride.classification === 'facility' || ride.classification === 'stall') ? false : (ride.breakdown !== 'none'),
                                downtime: ride.downtime / 100,
                                apprx_yearly_running_cost: ride.runningCost * 16 / 10,
                                age: ride.age,
                                lifetime_profit: ride.totalProfit / 10,
                            };
                            
                            rideData.push(rideInfo);
                        }
                        console.log("JSON Action Bridge: Sending response with " + rideData.length + " rides");
                        sendResponse(conn, {
                            status: "ok",
                            result: {
                                error: 0,
                                cost: 0,
                                rides: rideData
                            }
                        });
                        return; // CRITICAL: Return early to prevent execution as game action
                    } catch (e) {
                        console.log("JSON Action Bridge: Error getting ride info: " + e.message);
                        sendResponse(conn, {
                            status: "error",
                            message: "Failed to get ride info: " + e.message
                        });
                        return;
                    }
                }

// #endregion Special Actions

// #region Game Actions (executeAction fallback)
                // GAME ACTIONS: Pass through to OpenRCT2's context.executeAction()
                // All actions that aren't special actions get executed as game actions
                // This is OpenRCT2's standard action system for modifying game state
                
                console.log("JSON Action Bridge: Executing game action: '" + normalizedAction + "'");
                
                // Execute the game action using OpenRCT2's scripting API
                // context.executeAction(action, args, callback) is the standard API
                context.executeAction(normalizedAction, args, function(result) {
                    // This callback is called when the action completes
                    // result contains { error: code, cost: amount }
                    if (result.error === 0) {
                        console.log("JSON Action Bridge: Action '" + normalizedAction + "' succeeded (cost: " + result.cost + ")");
                        sendResponse(conn, {
                            status: "ok",
                            result: {
                                error: 0,
                                cost: result.cost || 0
                            }
                        });
                    } else {
                        console.log("JSON Action Bridge: Action '" + normalizedAction + "' failed with error: " + result.error);
                        sendResponse(conn, {
                            status: "error",
                            error: result.error,
                            errorTitle: "Action failed",
                            errorMessage: "Action '" + normalizedAction + "' failed with error code " + result.error,
                            cost: result.cost || 0
                        });
                    }
                });

// #endregion Game Actions
            } catch (e) {
                console.log("JSON Action Bridge: Error handling message: " + e.message);
                sendResponse(conn, {
                    status: "error",
                    message: "Error: " + e.message
                });
            }
        }
        
        /**
         * Send a JSON response back to the client over TCP
         * Protocol: Newline-delimited JSON
         */
        function sendResponse(conn, data) {
            try {
                var jsonStr = JSON.stringify(data);
                conn.send((jsonStr + "\n").encode());
            } catch (e) {
                console.log("JSON Action Bridge: Error sending response: " + e.message);
            }
        }
    }
});