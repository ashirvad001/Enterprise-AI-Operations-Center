import { render, screen } from '@testing-library/react'
import { Card } from '../app/components/Card'

describe('Card Component', () => {
  it('renders a Card with a title', () => {
    render(<Card title="Test Title">Card Content</Card>)
    
    const heading = screen.getByRole('heading', { level: 3 })
    expect(heading).toHaveTextContent('Test Title')
    expect(screen.getByText('Card Content')).toBeInTheDocument()
  })

  it('renders without a title', () => {
    render(<Card>Just Content</Card>)
    
    const heading = screen.queryByRole('heading')
    expect(heading).not.toBeInTheDocument()
    expect(screen.getByText('Just Content')).toBeInTheDocument()
  })
})
