CREATE_CHANNEL = """
    mutation {
        channelCreate(
            input: {
                isActive: true, 
                name: "myChannel", 
                slug: "myChannel", 
                currencyCode: "PLN"
            }
        ) {
            channelErrors {
                field
                message
            }
            channel {
                slug
            }
        }
    }
"""
