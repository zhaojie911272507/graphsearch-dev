declare module 'react-cytoscapejs' {
  import * as React from 'react'
  import cytoscape, { Core, ElementDefinition, LayoutOptions } from 'cytoscape'

  interface ReactCytoscapeProps {
    elements: ElementDefinition[]
    stylesheet?: any[]
    style?: React.CSSProperties
    layout?: LayoutOptions
    cy?: (cy: Core) => void
    wheelSensitivity?: number
    minZoom?: number
    maxZoom?: number
  }

  const CytoscapeComponent: React.FC<ReactCytoscapeProps>
  export default CytoscapeComponent
}